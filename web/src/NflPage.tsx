import { useEffect, useState } from 'react'
import { ArrowRight, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { fetchNflGames, fetchNflStandings, fetchNflSyncStatus, type NflGame, type NflStanding, type NflSyncStatus } from './nflData'

type PageState = 'loading' | 'ready' | 'empty' | 'error'
type View = 'schedule' | 'scores' | 'standings'
const finalStatuses = new Set(['FT', 'AOT', 'CANC', 'ABD', 'WO'])

function formatKickoff(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York',
  }).format(new Date(value))
}

function formatUpdated(value?: string | null): string {
  if (!value) return 'Sync pending'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' }).format(new Date(value))
}

function TeamLine({ name, logo, score }: { name: string; logo: string | null; score: number | null }) {
  return <div className="nfl-team-line">
    {logo && <img src={logo} alt="" loading="lazy" />}
    <span>{name}</span>
    {score !== null && <strong>{score}</strong>}
  </div>
}

export default function NflPage() {
  const [games, setGames] = useState<NflGame[]>([])
  const [standings, setStandings] = useState<NflStanding[]>([])
  const [syncState, setSyncState] = useState<NflSyncStatus[]>([])
  const [state, setState] = useState<PageState>('loading')
  const [view, setView] = useState<View>('schedule')
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchNflGames(), fetchNflStandings(), fetchNflSyncStatus()])
      .then(([gameRows, standingRows, syncRows]) => {
        if (cancelled) return
        setGames(gameRows)
        setStandings(standingRows)
        setSyncState(syncRows)
        setState(gameRows.length || standingRows.length ? 'ready' : 'empty')
      })
      .catch(() => { if (!cancelled) setState('error') })
    return () => { cancelled = true }
  }, [retryCount])

  const newestSync = syncState.filter((item) => item.sync_key === 'daily' && item.success).sort((a, b) => Date.parse(b.last_success_at || '') - Date.parse(a.last_success_at || ''))[0]
  const upcoming = games.filter((game) => !finalStatuses.has(game.status_short)).sort((a, b) => Date.parse(a.kickoff_at) - Date.parse(b.kickoff_at))
  const finalGames = games.filter((game) => finalStatuses.has(game.status_short)).sort((a, b) => Date.parse(b.kickoff_at) - Date.parse(a.kickoff_at))
  const groupedStandings = ['AFC', 'NFC'].map((conference) => ({
    conference,
    rows: standings.filter((standing) => standing.conference?.toUpperCase() === conference).sort((a, b) => (a.division || '').localeCompare(b.division || '') || a.standing_position - b.standing_position),
  }))

  return <main className="nfl-page">
    <header className="nfl-page-heading">
      <Link to="/" className="capper-back-link"><ArrowRight size={16} /> Home</Link>
      <p className="eyebrow">API-Sports · NFL · Season {games[0]?.season ?? standings[0]?.season ?? '—'}</p>
      <h1>Scores, schedule,<br />standings.</h1>
      <p className="nfl-page-intro">NFL data syncs server-side and is cached in Supabase. This page reads the cache; it never calls API-Sports directly.</p>
      <p className="nfl-last-sync">Last daily sync: <strong>{formatUpdated(newestSync?.last_success_at)}</strong></p>
    </header>

    <nav className="nfl-tabs" aria-label="NFL data views">
      {(['schedule', 'scores', 'standings'] as const).map((item) => <button key={item} className={view === item ? 'active' : ''} type="button" onClick={() => setView(item)}>{item}</button>)}
      {state === 'error' && <button className="nfl-retry" type="button" onClick={() => { setState('loading'); setRetryCount((count) => count + 1) }}><RefreshCw size={15} /> Retry</button>}
    </nav>

    {state === 'loading' && <p className="nfl-state">Loading NFL data…</p>}
    {state === 'error' && <p className="nfl-state">NFL data is unavailable. Check the Supabase migration and server sync.</p>}
    {state === 'empty' && <p className="nfl-state">No NFL data has synced yet. The Proxmox bot performs the initial sync on startup.</p>}

    {state === 'ready' && view === 'schedule' && <section className="nfl-games-list" aria-label="Upcoming NFL schedule">
      {upcoming.length ? upcoming.map((game) => <NflGameCard game={game} key={game.game_id} />) : <p className="nfl-state">No upcoming NFL games in the current season.</p>}
    </section>}

    {state === 'ready' && view === 'scores' && <section className="nfl-games-list" aria-label="NFL scores">
      {finalGames.length ? finalGames.map((game) => <NflGameCard game={game} key={game.game_id} />) : <p className="nfl-state">No final scores are available yet.</p>}
    </section>}

    {state === 'ready' && view === 'standings' && <section className="nfl-standings-grid">
      {groupedStandings.map(({ conference, rows }) => <div className="nfl-standings-panel" key={conference}>
        <h2>{conference}</h2>
        {rows.length ? <div className="nfl-standings-table" role="table" aria-label={`${conference} standings`}>
          <div className="nfl-standing-row nfl-standing-head" role="row"><span>Team</span><span>W-L-T</span><span>PF</span><span>PA</span><span>DIFF</span></div>
          {rows.map((standing) => <div className="nfl-standing-row" role="row" key={standing.team_id}>
            <span>{standing.division} · {standing.team_name}</span><span>{standing.wins}-{standing.losses}-{standing.ties}</span><span>{standing.points_for}</span><span>{standing.points_against}</span><span>{standing.point_difference > 0 ? '+' : ''}{standing.point_difference}</span>
          </div>)}
        </div> : <p className="nfl-state">Standings not published yet.</p>}
      </div>)}
    </section>}

    <footer className="nfl-page-footer"><span>Scores and standings update on a daily schedule; game scores refresh during active game windows.</span><span>Times shown in Eastern Time.</span></footer>
  </main>
}

function NflGameCard({ game }: { game: NflGame }) {
  return <article className="nfl-game-card nfl-game-card-large">
    <div className="nfl-game-meta"><span>{game.week || game.stage || `Week ${game.season}`}</span><time dateTime={game.kickoff_at}>{formatKickoff(game.kickoff_at)}</time></div>
    <div className="nfl-game-teams">
      <TeamLine name={game.away_team_name} logo={game.away_team_logo} score={game.away_score} />
      <TeamLine name={game.home_team_name} logo={game.home_team_logo} score={game.home_score} />
    </div>
    <div className="nfl-game-footer"><span>{game.venue_name ? `${game.venue_name}${game.venue_city ? ` · ${game.venue_city}` : ''}` : 'NFL'}</span><span className={`nfl-game-status${finalStatuses.has(game.status_short) ? ' is-final' : ''}`}>{game.status_long}</span></div>
  </article>
}