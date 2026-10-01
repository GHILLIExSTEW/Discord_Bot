import { supabase } from './supabaseClient'

export type NflGame = {
  game_id: number
  season: number
  stage: string | null
  week: string | null
  kickoff_at: string
  venue_name: string | null
  venue_city: string | null
  status_short: string
  status_long: string
  home_team_id: number | null
  home_team_name: string
  home_team_logo: string | null
  home_score: number | null
  away_team_id: number | null
  away_team_name: string
  away_team_logo: string | null
  away_score: number | null
  scores: {
    home?: { quarter_1?: number | null; quarter_2?: number | null; quarter_3?: number | null; quarter_4?: number | null; overtime?: number | null; total?: number | null }
    away?: { quarter_1?: number | null; quarter_2?: number | null; quarter_3?: number | null; quarter_4?: number | null; overtime?: number | null; total?: number | null }
  }
  synced_at: string
}

export type NflStanding = {
  season: number
  team_id: number
  team_name: string
  team_logo: string | null
  conference: string | null
  division: string | null
  standing_position: number
  wins: number
  losses: number
  ties: number
  points_for: number
  points_against: number
  point_difference: number
  streak: string | null
  synced_at: string
}

export type NflSyncStatus = { sync_key: string; last_success_at: string | null; success: boolean }

async function fetchRpc<T>(name: string): Promise<T[]> {
  const { data, error } = await supabase.rpc(name)
  if (error) throw error
  return (data ?? []) as T[]
}

export async function fetchNflGames(): Promise<NflGame[]> {
  return fetchRpc<NflGame>('public_nfl_games')
}

export async function fetchNflStandings(): Promise<NflStanding[]> {
  return fetchRpc<NflStanding>('public_nfl_standings')
}

export async function fetchNflSyncStatus(): Promise<NflSyncStatus[]> {
  return fetchRpc<NflSyncStatus>('public_nfl_data_status')
}