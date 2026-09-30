import { createContext, useContext, useEffect, useState } from 'react'
import {
  ArrowRight, BarChart3, Check, ChevronRight, Menu, MessageCircle,
  ShieldCheck, X,
} from 'lucide-react'
import {
  BrowserRouter, Link, NavLink, Outlet, Route, Routes, useNavigate, useParams,
  useLocation,
} from 'react-router-dom'
import './App.css'

type ResultStatus = 'win' | 'loss' | 'void' | 'partial' | 'regraded'
type Capper = { public_id: string; display_name: string }
type PublicResult = {
  id: number
  created_at: string
  settled_at: string | null
  sport: string
  selection: string
  odds: number
  units: number
  status: ResultStatus
  net_units: number
  capper: string
  capper_public_id: string | null
}
type CapperPlay = Omit<PublicResult, 'capper' | 'capper_public_id'>
type SiteData = {
  cappers: Capper[]
  results: PublicResult[]
  rosterLoading: boolean
  rosterUnavailable: boolean
  resultsLoading: boolean
  resultsUnavailable: boolean
}

const SiteDataContext = createContext<SiteData | null>(null)
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.replace(/\/$/, '')
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

async function fetchPublicView<T>(view: string, query: string): Promise<T> {
  if (!supabaseUrl || !supabaseAnonKey) throw new Error('Public data is not configured.')
  const response = await fetch(`${supabaseUrl}/rest/v1/${view}?${query}`, {
    headers: { apikey: supabaseAnonKey, Authorization: `Bearer ${supabaseAnonKey}` },
  })
  if (!response.ok) throw new Error(`Public data request failed: ${response.status}`)
  return response.json() as Promise<T>
}

function useSiteData(): SiteData {
  const data = useContext(SiteDataContext)
  if (!data) throw new Error('Site data is unavailable outside the application provider.')
  return data
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatOdds(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

function initials(value: string): string {
  return value.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('') || '?'
}

function DataProvider({ children }: { children: React.ReactNode }) {
  const [cappers, setCappers] = useState<Capper[]>([])
  const [results, setResults] = useState<PublicResult[]>([])
  const [rosterLoading, setRosterLoading] = useState(true)
  const [rosterUnavailable, setRosterUnavailable] = useState(false)
  const [resultsLoading, setResultsLoading] = useState(true)
  const [resultsUnavailable, setResultsUnavailable] = useState(false)

  useEffect(() => {
    let active = true
    const refresh = () => {
      fetchPublicView<Capper[]>('public_cappers', 'select=public_id,display_name&order=display_name.asc')
        .then((data) => { if (active) { setCappers(data); setRosterUnavailable(false) } })
        .catch(() => { if (active) setRosterUnavailable(true) })
        .finally(() => { if (active) setRosterLoading(false) })
      fetchPublicView<PublicResult[]>('public_results', 'select=id,created_at,settled_at,sport,selection,odds,units,status,net_units,capper,capper_public_id&order=created_at.desc')
        .then((data) => { if (active) { setResults(data); setResultsUnavailable(false) } })
        .catch(() => { if (active) setResultsUnavailable(true) })
        .finally(() => { if (active) setResultsLoading(false) })
    }
    refresh()
    const refreshInterval = window.setInterval(refresh, 60_000)
    window.addEventListener('focus', refresh)
    return () => {
      active = false
      window.clearInterval(refreshInterval)
      window.removeEventListener('focus', refresh)
    }
  }, [])

  return <SiteDataContext.Provider value={{ cappers, results, rosterLoading, rosterUnavailable, resultsLoading, resultsUnavailable }}>{children}</SiteDataContext.Provider>
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function SiteLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)
  const links = [
    { to: '/results', label: 'Results' },
    { to: '/cappers', label: 'Cappers' },
    { to: '/membership', label: 'Membership' },
    { to: '/methodology', label: 'Method' },
    { to: '/community', label: 'Community' },
  ]

  return (
    <div className="site-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Playmaker Picks home" onClick={closeMenu}>
          <span className="brand-mark">PP</span><span className="brand-copy"><strong>Playmaker</strong><small>Picks</small></span>
        </Link>
        <nav className={menuOpen ? 'main-nav is-open' : 'main-nav'} aria-label="Primary navigation">
          {links.map((link) => <NavLink key={link.to} to={link.to} onClick={closeMenu} className={({ isActive }) => `${isActive ? 'active' : ''} ${link.to === '/community' ? 'nav-community' : ''}`}>
            {link.label}{link.to === '/community' && <ArrowRight size={16} />}
          </NavLink>)}
        </nav>
        <button className="menu-button" type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Toggle navigation">{menuOpen ? <X /> : <Menu />}</button>
      </header>
      <main id="top"><Outlet /></main>
      <footer className="site-footer">
        <div className="footer-brand"><span className="brand-mark">PP</span><p><strong>Playmaker Picks</strong><small>Operated by Playmaker Sports Analytics, LLC.</small></p></div>
        <div className="footer-links"><Link to="/methodology">Methodology</Link><a href="mailto:legal@playmakersportsanalytics.com">Legal</a><a href="mailto:support@playmakersportsanalytics.com">Support</a></div>
        <p className="disclaimer">Sports analysis and opinions for informational and entertainment purposes only. We do not accept or place wagers. No outcome or profit is guaranteed. Must be 21+.</p>
        <p className="copyright">© 2026 Playmaker Sports Analytics, LLC.</p>
      </footer>
    </div>
  )
}

function HomePage() {
  const { cappers, results, rosterLoading, resultsLoading } = useSiteData()
  const recentResults = results.slice(0, 3)

  return (
    <>
      <section className="hero-section">
        <div className="hero-content reveal">
          <p className="eyebrow"><span className="live-dot" /> Independent sports analysis</p>
          <h1>Playmaker<br />Picks</h1>
          <p className="hero-copy">The play is only half the story. Follow the verified record, meet the analysts, and see how every result is graded.</p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/results">Explore verified results <ArrowRight size={18} /></Link>
            <Link className="button button-quiet" to="/community"><MessageCircle size={18} /> Join the community</Link>
          </div>
        </div>
        <div className="slate-board reveal reveal-delay">
          <div className="board-header"><div><span>Playmaker ledger</span><strong>Evidence over promises</strong></div><span className="board-state"><ShieldCheck size={14} /> Verified records</span></div>
          <div className="slate-metrics">
            <div><span>Settled results</span><strong>{resultsLoading ? '—' : results.length}</strong></div>
            <div><span>Authorized cappers</span><strong>{rosterLoading ? '—' : cappers.length}</strong></div>
            <div><span>Public record</span><strong>Open</strong></div>
          </div>
          <Link className="home-ledger-link" to="/results"><span><small>Public performance ledger</small><strong>See every settled result</strong></span><ChevronRight size={20} /></Link>
        </div>
        <div className="trust-strip">
          <span><ShieldCheck size={18} /> Timestamped records</span>
          <span><BarChart3 size={18} /> Unit-based analytics</span>
          <span><Check size={18} /> Wins and losses stay visible</span>
        </div>
      </section>
      <section className="home-sections">
        <div className="section-heading">
          <div><p className="eyebrow">Find your way in</p><h2>One record.<br />Every angle.</h2></div>
          <p>Explore the results ledger, learn who is authorized to post, and review the published grading method before joining the community.</p>
        </div>
        <div className="home-link-grid">
          <Link to="/results"><span>01 / Results</span><strong>Read the ledger</strong><ArrowRight size={20} /></Link>
          <Link to="/cappers"><span>02 / Cappers</span><strong>Meet the analysts</strong><ArrowRight size={20} /></Link>
          <Link to="/membership"><span>03 / Membership</span><strong>Compare access</strong><ArrowRight size={20} /></Link>
        </div>
        <div className="home-recent">
          <div className="profile-section-heading"><h2>Recent results</h2><Link to="/results">Full ledger <ArrowRight size={16} /></Link></div>
          {recentResults.length ? <ResultsTable results={recentResults} compact /> : <p className="data-message">{resultsLoading ? 'Loading verified results…' : 'No settled public results are available yet.'}</p>}
        </div>
      </section>
    </>
  )
}

function ResultsTable({ results, compact = false }: { results: PublicResult[]; compact?: boolean }) {
  return <div className="results-table" role="table" aria-label={compact ? 'Recent verified results' : 'Verified public results'}>
    <div className="result-row result-head" role="row"><span>Date</span><span>Play</span><span>Capper</span><span>Risk</span><span>Result</span><span>Net</span></div>
    {results.map((result) => <div className="result-row" role="row" key={result.id}>
      <span className="result-date">{formatDate(result.created_at)}<small>{result.sport}</small></span>
      <span className="result-selection">{result.selection}<small>{formatOdds(result.odds)}</small></span>
      <span>{result.capper_public_id ? <Link to={`/cappers/${result.capper_public_id}`}>{result.capper}</Link> : result.capper}</span>
      <span>{Number(result.units).toFixed(2)}u</span>
      <span><mark className={`status status-${result.status}`}>{result.status}</mark></span>
      <span className={Number(result.net_units) > 0 ? 'net-positive' : Number(result.net_units) < 0 ? 'net-negative' : ''}>{Number(result.net_units) > 0 ? '+' : ''}{Number(result.net_units).toFixed(2)}u</span>
    </div>)}
    {!results.length && <p className="data-message">No settled public results are available.</p>}
  </div>
}

function ResultsPage() {
  const { results, resultsLoading, resultsUnavailable } = useSiteData()
  const [sport, setSport] = useState('All')
  const sports = ['All', ...Array.from(new Set(results.map((result) => result.sport)))]
  const visibleResults = sport === 'All' ? results : results.filter((result) => result.sport === sport)
  return <section className="content-page results-section">
    <div className="section-heading"><div><p className="eyebrow">The public ledger</p><h1>Receipts, not promises.</h1></div><p>Every settled official play appears with its original line, risk, author, and final grade. No deleted losses. No selective history.</p></div>
    <div className="results-toolbar"><div className="filter-group" aria-label="Filter results by sport">{sports.map((item) => <button className={sport === item ? 'active' : ''} type="button" key={item} onClick={() => setSport(item)}>{item}</button>)}</div><span>Settled results</span></div>
    {resultsUnavailable ? <p className="data-message">Verified results are temporarily unavailable.</p> : resultsLoading ? <p className="data-message">Loading verified results…</p> : <ResultsTable results={visibleResults} />}
    <div className="proof-band"><div className="proof-copy"><p className="eyebrow">Built around the record</p><h2>One scoreboard.<br />Every angle.</h2><p>Review every public result alongside the grading method used to settle it.</p><Link to="/methodology">Read our grading method <ArrowRight size={17} /></Link></div><div className="proof-visual"><img src="/growth.png" alt="Playmaker Picks performance graphic" /></div></div>
  </section>
}

function CappersPage() {
  const { cappers, rosterLoading, rosterUnavailable } = useSiteData()
  return <section className="content-page cappers-section">
    <div className="section-heading"><div><p className="eyebrow">Authorized contributors</p><h1>Know who made the call.</h1></div><p>Capper access follows the authorized Discord role. Open a profile for settled-play analytics and sport-by-sport results.</p></div>
    {rosterUnavailable ? <p className="data-message">The authorized capper roster is temporarily unavailable.</p> : rosterLoading ? <p className="data-message">Loading authorized cappers…</p> : cappers.length ? <div className="capper-grid">{cappers.map((capper, index) => <article className="capper-card" key={capper.public_id}>
      <div className={`capper-avatar avatar-${index % 3 + 1}`}>{initials(capper.display_name)}</div><span className="capper-index">{String(index + 1).padStart(2, '0')}</span>
      <h2>{capper.display_name}</h2><strong>Authorized contributor</strong><p>Current member of the authorized Playmaker Discord role.</p>
      <Link to={`/cappers/${capper.public_id}`}>View analytics <ChevronRight size={16} /></Link>
    </article>)}</div> : <p className="data-message">No authorized cappers are currently listed.</p>}
  </section>
}

function CapperProfilePage() {
  const { capperId = '' } = useParams()
  const { cappers, rosterLoading } = useSiteData()
  const navigate = useNavigate()
  const capper = cappers.find((item) => item.public_id === capperId) ?? null
  const [plays, setPlays] = useState<CapperPlay[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!capper) return
    let active = true
    fetchPublicView<CapperPlay[]>('public_capper_plays', `capper_public_id=eq.${encodeURIComponent(capper.public_id)}&select=id,created_at,settled_at,sport,selection,odds,units,status,net_units&order=created_at.desc`)
      .then((data) => { if (active) setPlays(data) })
      .catch(() => { if (active) setError(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [capper])

  if (rosterLoading) return <p className="data-message content-page">Loading capper profile…</p>
  if (!capper) return <section className="capper-profile"><button className="profile-back" type="button" onClick={() => navigate('/cappers')}><ArrowRight size={16} /> Back to cappers</button><div className="profile-empty"><p className="eyebrow">Profile unavailable</p><h1>This capper is no longer active.</h1><p>Only members with the authorized Discord role have a public profile.</p></div></section>

  const wins = plays.filter((play) => play.status === 'win').length
  const losses = plays.filter((play) => play.status === 'loss').length
  const decided = wins + losses
  const netUnits = plays.reduce((total, play) => total + Number(play.net_units), 0)
  const riskedUnits = plays.filter((play) => play.status !== 'void').reduce((total, play) => total + Number(play.units), 0)
  const sportStats = Array.from(plays.reduce((summary, play) => {
    const sport = summary.get(play.sport) ?? { plays: 0, wins: 0, losses: 0, net: 0 }
    sport.plays += 1
    sport.wins += Number(play.status === 'win')
    sport.losses += Number(play.status === 'loss')
    sport.net += Number(play.net_units)
    summary.set(play.sport, sport)
    return summary
  }, new Map<string, { plays: number; wins: number; losses: number; net: number }>()).entries())

  return <section className="capper-profile">
    <button className="profile-back" type="button" onClick={() => navigate('/cappers')}><ArrowRight size={16} /> Back to cappers</button>
    <header className="profile-heading"><span className="capper-avatar">{initials(capper.display_name)}</span><div><p className="eyebrow">Authorized contributor</p><h1>{capper.display_name}</h1><p>Performance from settled, recorded plays.</p></div></header>
    {error ? <p className="data-message">Capper analytics are temporarily unavailable.</p> : loading ? <p className="data-message">Loading verified analytics…</p> : <>
      <div className="profile-metrics"><article><span>Settled plays</span><strong>{plays.length}</strong></article><article><span>Record</span><strong>{wins}-{losses}</strong></article><article><span>Win rate</span><strong>{decided ? `${(wins / decided * 100).toFixed(1)}%` : '—'}</strong></article><article><span>Net units</span><strong className={netUnits > 0 ? 'net-positive' : netUnits < 0 ? 'net-negative' : ''}>{netUnits > 0 ? '+' : ''}{netUnits.toFixed(2)}u</strong></article><article><span>ROI</span><strong>{riskedUnits ? `${(netUnits / riskedUnits * 100).toFixed(1)}%` : '—'}</strong></article></div>
      <div className="profile-section-heading"><h2>Sport breakdown</h2><span>Settled plays</span></div>
      {sportStats.length ? <div className="profile-sports">{sportStats.map(([sport, stats]) => <article key={sport}><strong>{sport}</strong><span>{stats.plays} plays · {stats.wins}-{stats.losses}</span><b className={stats.net > 0 ? 'net-positive' : stats.net < 0 ? 'net-negative' : ''}>{stats.net > 0 ? '+' : ''}{stats.net.toFixed(2)}u</b></article>)}</div> : <p className="data-message">No settled plays are available yet.</p>}
      <div className="profile-section-heading"><h2>Play history</h2><span>Open selections are never shown publicly</span></div>
      <div className="results-table profile-results" role="table" aria-label="Capper settled play history"><div className="result-row result-head" role="row"><span>Date</span><span>Sport</span><span>Play</span><span>Odds</span><span>Risk</span><span>Result</span><span>Net</span></div>{plays.map((play) => <div className="result-row" role="row" key={play.id}><span>{formatDate(play.created_at)}</span><span>{play.sport}</span><span className="result-selection">{play.selection}</span><span>{formatOdds(play.odds)}</span><span>{Number(play.units).toFixed(2)}u</span><span><mark className={`status status-${play.status}`}>{play.status}</mark></span><span className={Number(play.net_units) > 0 ? 'net-positive' : Number(play.net_units) < 0 ? 'net-negative' : ''}>{Number(play.net_units) > 0 ? '+' : ''}{Number(play.net_units).toFixed(2)}u</span></div>)}{!plays.length && <p className="data-message">No settled plays are available yet.</p>}</div>
    </>}
  </section>
}

const plans = [
  { name: 'Free', price: '$0', description: 'See how we work before you join the card.', features: ['Verified public record', 'Weekly recap', 'Occasional free analysis', 'Community announcements'], action: 'Join the free community' },
  { name: 'Starter', price: '$9.99', description: 'A focused card on active slates, without the noise.', features: ['Typically 1–2 curated plays', 'Standard Discord alerts', 'Full result tracking', 'Starter discussion access'], action: 'Get launch updates' },
  { name: 'All Access', price: '$19.99', description: 'Every official play, as soon as it posts.', features: ['Every approved capper', 'Real-time alerts', 'Full analysis and archive', 'Complete clubhouse access'], action: 'Get launch updates', featured: true },
]

function MembershipPage() {
  return <section className="content-page plans-section"><div className="section-heading light"><div><p className="eyebrow">Membership</p><h1>Pick your seat.</h1></div><p>Plans below are proposals only. Payment enrollment stays closed until provider and business approvals are complete.</p></div><div className="plan-grid">{plans.map((plan) => <article className={plan.featured ? 'plan-card featured' : 'plan-card'} key={plan.name}>{plan.featured && <span className="plan-flag">Full card</span>}<h2>{plan.name}</h2><div className="price"><strong>{plan.price}</strong><span>{plan.price !== '$0' ? '/ month' : 'free'}</span></div><p>{plan.description}</p><ul>{plan.features.map((feature) => <li key={feature}><Check size={17} />{feature}</li>)}</ul><a className="button plan-button" href="mailto:support@playmakersportsanalytics.com?subject=Playmaker%20Picks%20launch%20updates">{plan.action}<ArrowRight size={17} /></a></article>)}</div><p className="plans-note">Prices are proposed and may change before checkout opens. No outcome or profit is guaranteed. No-play days can occur.</p></section>
}

function MethodologyPage() {
  const steps = [
    ['01', 'Post', 'Every official play records its author, available odds, units, and publish time before the event begins.'],
    ['02', 'Track', 'The original position stays visible while open. Corrections leave an audit trail.'],
    ['03', 'Settle', 'Wins, losses, voids, and partial results use one published grading method.'],
    ['04', 'Review', 'Public records roll into capper, sport, weekly, monthly, and all-time views.'],
  ]
  return <section className="content-page method-page"><div className="section-heading"><div><p className="eyebrow">How the board works</p><h1>Clarity before confidence.</h1></div><p>Our methodology is designed to keep posted selections, grading, and historical performance reviewable.</p></div><div className="method-steps">{steps.map(([number, title, copy]) => <article key={number}><span>{number}</span><div><h2>{title}</h2><p>{copy}</p></div></article>)}</div><p className="method-disclaimer">Sports analysis is informational and does not guarantee a particular result or profit. We do not accept or place wagers.</p></section>
}

function CommunityPage() {
  return <section className="community-page"><div><p className="eyebrow">The clubhouse</p><h1>The card moves fast.<br />The record stays put.</h1></div><div className="community-copy"><p>Discord is the live alert and conversation channel. The website keeps the durable analysis, public results, and capper performance history.</p><a className="button button-accent" href="mailto:support@playmakersportsanalytics.com?subject=Playmaker%20Picks%20Discord%20invite"><MessageCircle size={18} /> Request a Discord invite</a></div></section>
}

function NotFoundPage() {
  return <section className="content-page profile-empty"><p className="eyebrow">Page not found</p><h1>That page isn’t on the board.</h1><p><Link to="/">Return to Playmaker Picks</Link></p></section>
}

function SiteApp() {
  return <BrowserRouter><ScrollToTop /><DataProvider><Routes><Route element={<SiteLayout />}>
    <Route index element={<HomePage />} />
    <Route path="results" element={<ResultsPage />} />
    <Route path="cappers" element={<CappersPage />} />
    <Route path="cappers/:capperId" element={<CapperProfilePage />} />
    <Route path="membership" element={<MembershipPage />} />
    <Route path="methodology" element={<MethodologyPage />} />
    <Route path="community" element={<CommunityPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes></DataProvider></BrowserRouter>
}

export default SiteApp
