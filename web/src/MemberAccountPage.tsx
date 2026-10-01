import { useEffect, useState, type FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { LogOut, ShieldCheck } from 'lucide-react'
import { supabase } from './supabaseClient'

type SportOption = { id: number; api_slug: string; name: string }
type CapperOption = { sport_id: number; sport: string; capper_name: string }
type MemberProfile = { age_verified_at: string | null }
type FavoriteSport = { sport_id: number }
type FavoriteCapper = { sport_id: number; capper_name: string }
type PageState = 'loading' | 'ready' | 'error'

function capperKey(sportId: number, capperName: string): string {
  return `${sportId}::${capperName}`
}

export default function MemberAccountPage() {
  const [session, setSession] = useState<Session | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [profile, setProfile] = useState<MemberProfile | null>(null)
  const [sports, setSports] = useState<SportOption[]>([])
  const [cappers, setCappers] = useState<CapperOption[]>([])
  const [favoriteSportIds, setFavoriteSportIds] = useState<number[]>([])
  const [favoriteCapperKeys, setFavoriteCapperKeys] = useState<string[]>([])
  const [birthDate, setBirthDate] = useState('')
  const [pageState, setPageState] = useState<PageState>('loading')
  const [busyKey, setBusyKey] = useState('')
  const [message, setMessage] = useState('')
  const [retryCount, setRetryCount] = useState(0)
  const signedInUserId = session?.user.id

  useEffect(() => {
    let cancelled = false
    supabase.auth.getSession().then(({ data, error }) => {
      if (cancelled) return
      if (error) setMessage('Could not check your sign-in session. Try again.')
      setSession(data.session)
      setAuthReady(true)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      if (!nextSession) {
        setProfile(null)
        setSports([])
        setCappers([])
        setFavoriteSportIds([])
        setFavoriteCapperKeys([])
        setPageState('ready')
      } else {
        setPageState('loading')
      }
    })
    return () => {
      cancelled = true
      subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    if (!authReady || !signedInUserId) return
    let cancelled = false
    void (async () => {
      try {
        const [profileResult, sportsResult, cappersResult] = await Promise.all([
          supabase.from('member_profiles').select('age_verified_at').eq('user_id', signedInUserId).maybeSingle(),
          supabase.rpc('public_favorite_sports'),
          supabase.rpc('public_favorite_cappers'),
        ])
        if (profileResult.error) throw profileResult.error
        if (sportsResult.error) throw sportsResult.error
        if (cappersResult.error) throw cappersResult.error
        const nextProfile = profileResult.data as MemberProfile | null
        setProfile(nextProfile)
        setSports((sportsResult.data ?? []) as SportOption[])
        setCappers((cappersResult.data ?? []) as CapperOption[])

        if (nextProfile?.age_verified_at) {
          const [favoriteSportsResult, favoriteCappersResult] = await Promise.all([
            supabase.from('member_favorite_sports').select('sport_id').eq('user_id', signedInUserId),
            supabase.from('member_favorite_cappers').select('sport_id,capper_name').eq('user_id', signedInUserId),
          ])
          if (favoriteSportsResult.error) throw favoriteSportsResult.error
          if (favoriteCappersResult.error) throw favoriteCappersResult.error
          if (cancelled) return
          setFavoriteSportIds(((favoriteSportsResult.data ?? []) as FavoriteSport[]).map((row) => row.sport_id))
          setFavoriteCapperKeys(((favoriteCappersResult.data ?? []) as FavoriteCapper[]).map((row) => capperKey(row.sport_id, row.capper_name)))
        }
        if (!cancelled) {
          setMessage('')
          setPageState('ready')
        }
      } catch {
        if (!cancelled) {
          setMessage('Your account settings could not be loaded. Check the account migration and try again.')
          setPageState('error')
        }
      }
    })()
    return () => { cancelled = true }
  }, [authReady, retryCount, signedInUserId])

  async function signInWithDiscord() {
    setMessage('')
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'discord',
      options: { redirectTo: `${window.location.origin}/account` },
    })
    if (error) setMessage('Discord sign-in could not start. Check the configured OAuth provider.')
  }

  async function verifyAge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!birthDate) {
      setMessage('Enter your date of birth to verify age.')
      return
    }
    setBusyKey('age')
    setMessage('')
    try {
      const { data, error } = await supabase.rpc('verify_member_age', { p_birth_date: birthDate })
      if (error) throw error
      if (data !== true) {
        setMessage('You must be at least 21 to create a member account.')
        return
      }
      setPageState('loading')
      setProfile({ age_verified_at: new Date().toISOString() })
      setRetryCount((count) => count + 1)
    } catch {
      setMessage('Age verification could not be completed. Try again.')
    } finally {
      setBusyKey('')
      setBirthDate('')
    }
  }

  async function toggleSport(sportId: number) {
    if (!session) return
    const isFavorite = favoriteSportIds.includes(sportId)
    const key = `sport:${sportId}`
    setBusyKey(key)
    setFavoriteSportIds((current) => isFavorite ? current.filter((id) => id !== sportId) : [...current, sportId])
    setMessage('Saving sport preference…')
    try {
      const result = isFavorite
        ? await supabase.from('member_favorite_sports').delete().eq('user_id', session.user.id).eq('sport_id', sportId)
        : await supabase.from('member_favorite_sports').insert({ user_id: session.user.id, sport_id: sportId })
      if (result.error) throw result.error
      setMessage('Sport preference saved.')
    } catch {
      setFavoriteSportIds((current) => isFavorite ? [...current, sportId] : current.filter((id) => id !== sportId))
      setMessage('Could not save that sport. Confirm your age verification is complete and retry.')
    } finally {
      setBusyKey('')
    }
  }

  async function toggleCapper(capper: CapperOption) {
    if (!session) return
    const key = capperKey(capper.sport_id, capper.capper_name)
    const isFavorite = favoriteCapperKeys.includes(key)
    setBusyKey(`capper:${key}`)
    setFavoriteCapperKeys((current) => isFavorite ? current.filter((item) => item !== key) : [...current, key])
    setMessage('Saving capper preference…')
    try {
      const result = isFavorite
        ? await supabase.from('member_favorite_cappers').delete().eq('user_id', session.user.id).eq('sport_id', capper.sport_id).eq('capper_name', capper.capper_name)
        : await supabase.from('member_favorite_cappers').insert({ user_id: session.user.id, sport_id: capper.sport_id, capper_name: capper.capper_name })
      if (result.error) throw result.error
      setMessage('Capper preference saved.')
    } catch {
      setFavoriteCapperKeys((current) => isFavorite ? [...current, key] : current.filter((item) => item !== key))
      setMessage('Could not save that capper. Confirm your age verification is complete and retry.')
    } finally {
      setBusyKey('')
    }
  }

  async function signOut() {
    const { error } = await supabase.auth.signOut()
    if (error) setMessage('Could not sign out. Try again.')
  }

  if (!authReady || (session && pageState === 'loading')) {
    return <main className="account-page"><p className="account-state">Loading account…</p></main>
  }

  if (!session) {
    return <main className="account-page">
      <section className="account-panel account-sign-in">
        <p className="eyebrow">Member account</p>
        <h1>Your picks.<br />Your sports.</h1>
        <p>Sign in with Discord to save favorite sports and cappers.</p>
        {message && <p className="account-message" role="alert">{message}</p>}
        <button className="button button-primary" type="button" onClick={signInWithDiscord}>Continue with Discord</button>
      </section>
    </main>
  }

  if (pageState === 'error') {
    return <main className="account-page">
      <section className="account-panel">
        <p className="eyebrow">Member account</p>
        <h1>Account settings<br />unavailable.</h1>
        <p className="account-message" role="alert">{message}</p>
        <button className="button button-primary" type="button" onClick={() => { setPageState('loading'); setRetryCount((count) => count + 1) }}>Retry</button>
        <button className="account-sign-out" type="button" onClick={signOut}>Sign out</button>
      </section>
    </main>
  }

  if (!profile?.age_verified_at) {
    return <main className="account-page">
      <section className="account-panel account-age-panel">
        <p className="eyebrow"><ShieldCheck size={16} /> Age verification</p>
        <h1>Members must<br />be 21+.</h1>
        <p>Enter your date of birth to confirm you meet the age requirement. We store only the verification timestamp, not your birth date.</p>
        <form className="age-verification-form" onSubmit={verifyAge}>
          <label htmlFor="member-birth-date">Date of birth</label>
          <input id="member-birth-date" type="date" value={birthDate} onChange={(event) => setBirthDate(event.target.value)} autoComplete="bday" required />
          {message && <p className="account-message" role="alert">{message}</p>}
          <button className="button button-primary" type="submit" disabled={busyKey === 'age'}>{busyKey === 'age' ? 'Verifying…' : 'Verify age & continue'}</button>
        </form>
        <button className="account-sign-out" type="button" onClick={signOut}>Sign out</button>
      </section>
    </main>
  }

  const capperGroups = sports.map((sport) => ({
    sport,
    cappers: cappers.filter((capper) => capper.sport_id === sport.id),
  })).filter((group) => group.cappers.length)

  return <main className="account-page">
    <header className="account-page-heading">
      <div><p className="eyebrow">Member account</p><h1>Your board.</h1><p>Choose the sports and cappers you want to follow.</p></div>
      <button className="account-sign-out" type="button" onClick={signOut}><LogOut size={16} /> Sign out</button>
    </header>
    {message && <p className="account-message" role="alert">{message}</p>}
    <section className="account-preferences">
      <div className="account-section-heading"><p className="eyebrow">01 · Sports</p><h2>Pick your sports.</h2></div>
      <div className="account-sports-list">
        {sports.map((sport) => <label className="account-choice" key={sport.id}>
          <input type="checkbox" checked={favoriteSportIds.includes(sport.id)} disabled={Boolean(busyKey)} onChange={() => toggleSport(sport.id)} />
          <span>{sport.name}</span>
        </label>)}
      </div>
    </section>
    <section className="account-preferences">
      <div className="account-section-heading"><p className="eyebrow">02 · Cappers</p><h2>Choose by sport.</h2></div>
      {capperGroups.length ? capperGroups.map((group) => <div className="account-capper-group" key={group.sport.id}>
        <h3>{group.sport.name}</h3>
        <div className="account-cappers-list">
          {group.cappers.map((capper) => {
            const key = capperKey(capper.sport_id, capper.capper_name)
            return <label className="account-choice" key={key}>
              <input type="checkbox" checked={favoriteCapperKeys.includes(key)} disabled={Boolean(busyKey)} onChange={() => toggleCapper(capper)} />
              <span>{capper.capper_name}</span>
            </label>
          })}
        </div>
      </div>) : <p className="account-state">Capper choices appear as public settled records are published.</p>}
    </section>
  </main>
}
