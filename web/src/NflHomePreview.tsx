import { useEffect, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { fetchNflGames, type NflGame } from './nflData'

function formatKickoff(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York',
  }).format(new Date(value))
}

function TeamLine({ name, logo, score }: { name: string; logo: string | null; score: number | null }) {
  return <div className="nfl-team-line">
    {logo && <img src={logo} alt="" loading="lazy" />}
    <span>{name}</span>
    {score !== null && <strong>{score}</strong>}
  </div>
}

export default function NflHomePreview() {
  const [games, setGames] = useState<NflGame[]>([])
  const [state, setState] = useState<'loading' | 'ready' | 'empty' | 'error'>('loading')

  useEffect(() => {
    let cancelled = false
    fetchNflGames()
      .then((rows) => {
        if (cancelled) return
        const now = Date.now()
        const finalStatuses = new Set(['FT', 'AOT', 'CANC', 'ABD', 'WO'])
        const upcoming = rows.filter((game) => !finalStatuses.has(game.status_short) && Date.parse(game.kickoff_at) >= now).sort((a, b) => Date.parse(a.kickoff_at) - Date.parse(b.kickoff_at))
        const recent = rows.filter((game) => finalStatuses.has(game.status_short)).sort((a, b) => Date.parse(b.kickoff_at) - Date.parse(a.kickoff_at))
        const chosen = upcoming.length ? upcoming.slice(0, 3) : recent.slice(0, 3)
        setGames(chosen)
        setState(chosen.length ? 'ready' : 'empty')
      })
      .catch(() => { if (!cancelled) setState('error') })
    return () => { cancelled = true }
  }, [])

  return <section className="nfl-preview">
    <div className="nfl-preview-heading">
      <div><p className="eyebrow">NFL · API-Sports</p><h2>Schedule & scores.</h2></div>
      <Link className="nfl-view-link" to="/nfl">Open NFL center <ArrowRight size={17} /></Link>
    </div>
    {state === 'loading' && <p className="nfl-state">Loading cached NFL data…</p>}
    {state === 'error' && <p className="nfl-state">NFL data will appear after the first server sync.</p>}
    {state === 'empty' && <p className="nfl-state">No NFL games are available for this season yet.</p>}
    {state === 'ready' && <div className="nfl-preview-grid">{games.map((game) => <article className="nfl-game-card" key={game.game_id}>
      <div className="nfl-game-meta"><span>{game.week || game.stage || `Week ${game.season}`}</span><span>{formatKickoff(game.kickoff_at)}</span></div>
      <TeamLine name={game.away_team_name} logo={game.away_team_logo} score={game.away_score} />
      <TeamLine name={game.home_team_name} logo={game.home_team_logo} score={game.home_score} />
      <span className="nfl-game-status">{game.status_long}</span>
    </article>)}</div>}
  </section>
}