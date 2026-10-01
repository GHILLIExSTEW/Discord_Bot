import { useEffect, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { supabase } from './supabaseClient'

type PublicMemberProfile = {
  display_name: string
  public_handle: string
  avatar_url: string | null
  created_at: string
  favorite_sports: { id: number; name: string }[]
  favorite_cappers: { sport: string; capper: string }[]
}

function initials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0] || '').join('').toUpperCase()
}

export default function MemberPublicPage({ handle }: { handle: string }) {
  const [profile, setProfile] = useState<PublicMemberProfile | null>(null)
  const [avatarFailed, setAvatarFailed] = useState(false)
  const [state, setState] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const { data, error } = await supabase.rpc('public_member_profile', { p_public_handle: handle })
        if (cancelled) return
        const value = data as PublicMemberProfile | null
        if (error || !value) {
          setState('unavailable')
          return
        }
        setProfile(value)
        setState('ready')
      } catch {
        if (!cancelled) setState('unavailable')
      }
    })()
    return () => { cancelled = true }
  }, [handle])

  const profileName = profile?.display_name
  useEffect(() => {
    document.title = profileName ? `${profileName} | Playmaker Picks` : 'Member Profile | Playmaker Picks'
  }, [profileName])

  if (state === 'loading') return <main className="member-public-page"><p className="account-state">Loading public profile…</p></main>
  if (state === 'unavailable' || !profile) return <main className="member-public-page"><p className="eyebrow">Member profile</p><h1>Profile unavailable.</h1><p>This profile is private or no longer available.</p><Link to="/">Return home <ArrowRight size={16} /></Link></main>

  const joined = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(new Date(profile.created_at))

  return <main className="member-public-page">
    <Link to="/" className="capper-back-link"><ArrowRight size={16} /> Home</Link>
    <section className="member-public-identity">
      {profile.avatar_url && !avatarFailed
        ? <img src={profile.avatar_url} alt={`${profile.display_name} avatar`} onError={() => setAvatarFailed(true)} />
        : <span className="member-public-avatar-fallback">{initials(profile.display_name)}</span>}
      <div><p className="eyebrow">Playmaker member</p><h1>{profile.display_name}</h1><p>@{profile.public_handle} · Member since {joined}</p></div>
    </section>
    <section className="member-public-favorites">
      <div className="account-section-heading"><p className="eyebrow">Following</p><h2>Sports & cappers.</h2></div>
      {profile.favorite_sports.length || profile.favorite_cappers.length ? <>
        {profile.favorite_sports.length > 0 && <div className="member-public-group"><h3>Sports</h3><div className="account-sports-list">{profile.favorite_sports.map((item) => <span className="account-choice" key={item.id}>{item.name}</span>)}</div></div>}
        {profile.favorite_cappers.length > 0 && <div className="member-public-group"><h3>Cappers</h3><div className="account-sports-list">{profile.favorite_cappers.map((item) => <span className="account-choice" key={`${item.sport}-${item.capper}`}><small>{item.sport}</small>{item.capper}</span>)}</div></div>}
      </> : <p className="account-state">No favorites shared yet.</p>}
    </section>
  </main>
}
