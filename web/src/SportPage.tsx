import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { sportsCatalog } from './sportsCatalog'

type Result = {
  settled_at: string
  sport: string
  capper: string
  selection: string
  odds: number
  units: number
  status: 'win' | 'loss' | 'void' | 'partial'
  net_units: number
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'America/New_York' }).format(new Date(value))
}

function signedUnits(value: number): string {
  const amount = Number(value)
  const sign = amount > 0 ? '+' : amount < 0 ? '-' : ''
  return `${sign}${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(Math.abs(amount))}u`
}

export default function SportPage({ slug, results, loadState }: { slug: string; results: Result[]; loadState: 'loading' | 'ready' | 'error' | 'configuration' }) {
  const sport = sportsCatalog.find((item) => item.slug === slug)
  if (!sport) return <main className="sport-page"><p className="eyebrow">Sports</p><h1>Sport not found.</h1><Link to="/">Return home <ArrowRight size={16} /></Link></main>

  const sportResults = results.filter((result) => result.sport.trim().toLowerCase() === sport.name.toLowerCase())
  const wins = sportResults.filter((result) => result.status === 'win').length
  const losses = sportResults.filter((result) => result.status === 'loss').length
  const net = sportResults.reduce((sum, result) => sum + Number(result.net_units), 0)

  return <main className="sport-page">
    <Link to="/" className="capper-back-link"><ArrowRight size={16} /> Home</Link>
    <header className="sport-page-heading">
      <p className="eyebrow">Sport record</p><h1>{sport.name}.</h1>
      <p>Official settled plays and performance for {sport.name}.</p>
    </header>
    {sport.slug === 'american-football' && <Link className="sport-feature-link" to="/nfl">Open NFL schedule, scores &amp; standings <ArrowRight size={16} /></Link>}
    <div className="sport-record-metrics">
      <div><span>Settled plays</span><strong>{loadState === 'ready' ? sportResults.length : '—'}</strong></div>
      <div><span>Record</span><strong>{loadState === 'ready' ? `${wins}-${losses}` : '—'}</strong></div>
      <div><span>Net units</span><strong className={net > 0 ? 'net-positive' : net < 0 ? 'net-negative' : ''}>{loadState === 'ready' ? signedUnits(net) : '—'}</strong></div>
    </div>
    <section className="sport-results">
      <div className="profile-section-heading"><p className="eyebrow">The settled ledger</p><h2>{sport.name} results.</h2></div>
      {loadState === 'loading' && <p className="results-empty">Loading {sport.name} results…</p>}
      {loadState === 'error' && <p className="results-empty">Results are temporarily unavailable.</p>}
      {loadState === 'configuration' && <p className="results-empty">Results aren’t connected yet.</p>}
      {loadState === 'ready' && sportResults.length === 0 && <p className="results-empty">No official settled {sport.name} plays have been published yet.</p>}
      {sportResults.length > 0 && <div className="results-table" role="table" aria-label={`${sport.name} settled plays`}>
        <div className="result-row result-head" role="row"><span>Date</span><span>Play</span><span>Capper</span><span>Odds</span><span>Result</span><span>Net</span></div>
        {sportResults.map((result, index) => <div className="result-row" role="row" key={`${result.settled_at}-${index}`}>
          <span className="result-date">{formatDate(result.settled_at)}</span>
          <span className="result-selection">{result.selection}<small>{result.odds > 0 ? '+' : ''}{result.odds}</small></span>
          <span>{result.capper}</span><span>{result.units}u</span>
          <span><mark className={`status status-${result.status}`}>{result.status}</mark></span>
          <span className={result.net_units > 0 ? 'net-positive' : result.net_units < 0 ? 'net-negative' : ''}>{signedUnits(result.net_units)}</span>
        </div>)}
      </div>}
    </section>
  </main>
}