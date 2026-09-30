import { useState } from 'react'
import {
  ArrowRight, BarChart3, Check, ChevronRight, Clock3, Menu,
  MessageCircle, ShieldCheck, Trophy, X,
} from 'lucide-react'
import './App.css'

type ResultStatus = 'Win' | 'Loss' | 'Void'
type Result = { date: string; sport: string; capper: string; selection: string; odds: string; units: string; status: ResultStatus; net: string }

const previewResults: Result[] = [
  { date: 'SEP 29', sport: 'NFL', capper: 'The Board', selection: 'Detroit +2.5', odds: '-110', units: '1.0u', status: 'Win', net: '+0.91u' },
  { date: 'SEP 28', sport: 'MLB', capper: 'Robin', selection: 'Seattle ML', odds: '+118', units: '1.0u', status: 'Loss', net: '-1.00u' },
  { date: 'SEP 28', sport: 'WNBA', capper: 'Ghillie', selection: 'Las Vegas -4', odds: '-105', units: '1.5u', status: 'Win', net: '+1.43u' },
  { date: 'SEP 27', sport: 'CFB', capper: 'The Board', selection: 'Oregon team total over', odds: '-115', units: '1.0u', status: 'Void', net: '0.00u' },
  { date: 'SEP 27', sport: 'MLB', capper: 'Robin', selection: 'Chicago F5 ML', odds: '-120', units: '1.0u', status: 'Win', net: '+0.83u' },
]

const cappers = [
  { initials: 'GS', name: 'Ghillie', focus: 'Market reads · Multi-sport', note: 'Process-first analysis with every result on the board.' },
  { initials: 'RB', name: 'Robin', focus: 'Research · MLB · NFL', note: 'Deep slate research and disciplined daily selection.' },
  { initials: 'PP', name: 'The Board', focus: 'Consensus · Best available', note: 'Only the strongest shared positions make the official card.' },
]

const plans = [
  { name: 'Free', price: '$0', description: 'See how we work before you join the card.', features: ['Verified public record', 'Weekly recap', 'Occasional free play', 'Community announcements'], action: 'Join the free community' },
  { name: 'Starter', price: '$9.99', description: 'A focused daily card without the noise.', features: ['Typically 1–2 curated plays', 'Standard Discord alerts', 'Full result tracking', 'Starter discussion access'], action: 'Get launch updates' },
  { name: 'All Access', price: '$19.99', description: 'Every official play, as soon as it posts.', features: ['Every approved capper', 'Real-time alerts', 'Full analysis and archive', 'Complete clubhouse access'], action: 'Get launch updates', featured: true },
]

function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [sport, setSport] = useState('All')
  const [freePlayOpen, setFreePlayOpen] = useState(false)
  const sports = ['All', ...Array.from(new Set(previewResults.map((result) => result.sport)))]
  const visibleResults = sport === 'All' ? previewResults : previewResults.filter((result) => result.sport === sport)
  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Playmaker Picks home" onClick={closeMenu}>
          <span className="brand-mark">PP</span>
          <span className="brand-copy"><strong>Playmaker</strong><small>Picks</small></span>
        </a>
        <nav className={menuOpen ? 'main-nav is-open' : 'main-nav'} aria-label="Primary navigation">
          <a href="#results" onClick={closeMenu}>Results</a>
          <a href="#cappers" onClick={closeMenu}>Cappers</a>
          <a href="#plans" onClick={closeMenu}>Membership</a>
          <a href="#method" onClick={closeMenu}>Method</a>
          <a className="nav-community" href="#community" onClick={closeMenu}>Join Discord <ArrowRight size={16} /></a>
        </nav>
        <button className="menu-button" type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Toggle navigation">{menuOpen ? <X /> : <Menu />}</button>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-content reveal">
            <p className="eyebrow"><span className="live-dot" /> Independent sports analysis</p>
            <h1>Playmaker<br />Picks</h1>
            <p className="hero-copy">The play is only half the story. See the line, the timestamp, the unit size, and every result that follows.</p>
            <div className="hero-actions">
              <a className="button button-primary" href="#results">View verified results <ArrowRight size={18} /></a>
              <a className="button button-quiet" href="#community"><MessageCircle size={18} /> Join Discord free</a>
            </div>
          </div>

          <div className="slate-board reveal reveal-delay">
            <div className="board-header">
              <div><span>Today’s card</span><strong>Wednesday · Sep 30</strong></div>
              <span className="board-state"><Clock3 size={14} /> Building</span>
            </div>
            <div className="slate-metrics">
              <div><span>Sports watched</span><strong>4</strong></div>
              <div><span>Plays posted</span><strong>1</strong></div>
              <div><span>Next review</span><strong>5:30 ET</strong></div>
            </div>
            <button className="free-play" type="button" onClick={() => setFreePlayOpen((open) => !open)} aria-expanded={freePlayOpen}>
              <span className="free-play-icon"><Trophy size={21} /></span>
              <span><small>Community free play</small><strong>{freePlayOpen ? 'Detroit +2.5 · -110' : 'Tap to reveal today’s sample'}</strong></span>
              <ChevronRight className={freePlayOpen ? 'rotated' : ''} size={20} />
            </button>
            <p className="preview-label">Preview card · Live coverage begins at launch</p>
          </div>

          <div className="trust-strip">
            <span><ShieldCheck size={18} /> Timestamped posts</span>
            <span><BarChart3 size={18} /> Unit-based tracking</span>
            <span><Check size={18} /> Wins and losses stay public</span>
          </div>
        </section>

        <section className="results-section" id="results">
          <div className="section-heading">
            <div><p className="eyebrow">The public ledger</p><h2>Receipts, not promises.</h2></div>
            <p>Every official play lands here with the original line, risk, author, and final grade. No deleted losses. No selective history.</p>
          </div>
          <div className="results-toolbar">
            <div className="filter-group" aria-label="Filter preview results by sport">
              {sports.map((item) => <button className={sport === item ? 'active' : ''} type="button" key={item} onClick={() => setSport(item)}>{item}</button>)}
            </div>
            <span>Preview data</span>
          </div>
          <div className="results-table" role="table" aria-label="Recent result preview">
            <div className="result-row result-head" role="row"><span>Date</span><span>Play</span><span>Capper</span><span>Risk</span><span>Result</span><span>Net</span></div>
            {visibleResults.map((result) => (
              <div className="result-row" role="row" key={`${result.date}-${result.selection}`}>
                <span className="result-date">{result.date}<small>{result.sport}</small></span>
                <span className="result-selection">{result.selection}<small>{result.odds}</small></span>
                <span>{result.capper}</span><span>{result.units}</span>
                <span><mark className={`status status-${result.status.toLowerCase()}`}>{result.status}</mark></span>
                <span className={result.status === 'Win' ? 'net-positive' : result.status === 'Loss' ? 'net-negative' : ''}>{result.net}</span>
              </div>
            ))}
          </div>
          <div className="proof-band">
            <div className="proof-copy">
              <p className="eyebrow">Built around the record</p><h3>One scoreboard.<br />Every angle.</h3>
              <p>Filter by capper, sport, date range, play type, and membership card. The same settled records power Discord recaps and the public site.</p>
              <a href="#method">Read our grading method <ArrowRight size={17} /></a>
            </div>
            <div className="proof-visual"><img src="/growth.png" alt="Playmaker Picks performance graphic" /></div>
          </div>
        </section>

        <section className="cappers-section" id="cappers">
          <div className="section-heading compact">
            <div><p className="eyebrow">The room</p><h2>Know who made the call.</h2></div>
            <p>Public summaries establish the record. Full profiles, analysis notes, and play archives live inside the clubhouse.</p>
          </div>
          <div className="capper-grid">
            {cappers.map((capper, index) => (
              <article className="capper-card" key={capper.name}>
                <div className={`capper-avatar avatar-${index + 1}`}>{capper.initials}</div><span className="capper-index">0{index + 1}</span>
                <h3>{capper.name}</h3><strong>{capper.focus}</strong><p>{capper.note}</p>
                <a href="#community">View public summary <ChevronRight size={16} /></a>
              </article>
            ))}
          </div>
        </section>

        <section className="plans-section" id="plans">
          <div className="section-heading light">
            <div><p className="eyebrow">Membership</p><h2>Pick your seat.</h2></div>
            <p>Start with the record, move to a focused card, or open the whole room. Paid membership enrollment opens soon.</p>
          </div>
          <div className="plan-grid">
            {plans.map((plan) => (
              <article className={plan.featured ? 'plan-card featured' : 'plan-card'} key={plan.name}>
                {plan.featured && <span className="plan-flag">Full card</span>}<h3>{plan.name}</h3>
                <div className="price"><strong>{plan.price}</strong><span>{plan.price !== '$0' ? '/ month' : 'forever'}</span></div>
                <p>{plan.description}</p><ul>{plan.features.map((feature) => <li key={feature}><Check size={17} />{feature}</li>)}</ul>
                <a className="button plan-button" href="mailto:support@playmakersportsanalytics.com?subject=Playmaker%20Picks%20launch%20updates">{plan.action}<ArrowRight size={17} /></a>
              </article>
            ))}
          </div>
          <p className="plans-note">Prices are proposed for launch and may change before checkout opens. No outcome or profit is guaranteed.</p>
        </section>

        <section className="method-section" id="method">
          <div className="method-intro"><p className="eyebrow">How the board works</p><h2>Clarity before confidence.</h2></div>
          <div className="method-steps">
            <article><span>01</span><div><h3>Post</h3><p>Every play records its author, odds, units, and publish time before the event begins.</p></div></article>
            <article><span>02</span><div><h3>Track</h3><p>The original position stays visible while open. Corrections leave an audit trail.</p></div></article>
            <article><span>03</span><div><h3>Settle</h3><p>Wins, losses, voids, and partial results use one published grading method.</p></div></article>
            <article><span>04</span><div><h3>Review</h3><p>Public records roll into capper, sport, weekly, monthly, and all-time views.</p></div></article>
          </div>
        </section>

        <section className="community-section" id="community">
          <div><p className="eyebrow">The clubhouse</p><h2>The card moves fast.<br />The record stays put.</h2></div>
          <div className="community-copy"><p>Discord carries live alerts and conversation. The website keeps the durable analysis, searchable discussion, and complete history.</p>
            <a className="button button-accent" href="mailto:support@playmakersportsanalytics.com?subject=Playmaker%20Picks%20Discord%20invite"><MessageCircle size={18} /> Request a Discord invite</a>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-brand"><span className="brand-mark">PP</span><p><strong>Playmaker Picks</strong><small>Operated by Playmaker Sports Analytics, LLC.</small></p></div>
        <div className="footer-links"><a href="#method">Methodology</a><a href="mailto:legal@playmakersportsanalytics.com">Legal</a><a href="mailto:support@playmakersportsanalytics.com">Support</a></div>
        <p className="disclaimer">Sports analysis and opinions for informational and entertainment purposes only. We do not accept or place wagers. No outcome or profit is guaranteed. Must be 21+.</p>
        <p className="copyright">© 2026 Playmaker Sports Analytics, LLC.</p>
      </footer>
    </div>
  )
}

export default App