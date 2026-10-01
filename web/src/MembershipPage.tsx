import { ArrowRight, Check } from 'lucide-react'
import { Link } from 'react-router-dom'

const plans = [
  { name: 'Free', price: '$0', summary: 'Start with the public record and community.', featured: false },
  { name: 'Starter', price: '$9.99', summary: 'A focused card for members who want curated plays.', featured: false },
  { name: 'All Access', price: '$19.99', summary: 'Every approved capper and the complete analysis archive.', featured: true },
]

const features = [
  { name: 'Public settled-play record', values: ['Included', 'Included', 'Included'] },
  { name: 'Personalized sports & capper follows', values: ['Included', 'Included', 'Included'] },
  { name: 'Weekly recap', values: ['Included', 'Included', 'Included'] },
  { name: 'Curated member card', values: ['—', 'Planned', 'Planned'] },
  { name: 'Member Discord alerts', values: ['—', 'Planned', 'Planned'] },
  { name: 'All approved cappers', values: ['—', '—', 'Planned'] },
  { name: 'Full analysis archive', values: ['—', '—', 'Planned'] },
]

export default function MembershipPage() {
  return <main className="membership-page">
    <Link to="/" className="capper-back-link"><ArrowRight size={16} /> Home</Link>
    <header className="membership-page-heading">
      <p className="eyebrow">Membership</p>
      <h1>Find your seat.</h1>
      <p>Compare the proposed Playmaker Picks memberships. Pricing and paid features are not final; checkout is not open.</p>
    </header>
    <section className="membership-plan-grid" aria-label="Proposed membership plans">
      {plans.map((plan) => <article className={`membership-plan${plan.featured ? ' is-featured' : ''}`} key={plan.name}>
        <p className="eyebrow">{plan.featured ? 'Full card' : 'Playmaker Picks'}</p>
        <h2>{plan.name}</h2>
        <p className="membership-price">{plan.price}<span>{plan.price === '$0' ? ' forever' : ' / month'}</span></p>
        <p>{plan.summary}</p>
        <a className="button membership-interest" href={`mailto:support@playmakersportsanalytics.com?subject=${encodeURIComponent(`Playmaker ${plan.name} membership interest`)}`}>Get launch updates <ArrowRight size={16} /></a>
      </article>)}
    </section>
    <section className="membership-breakdown">
      <div className="profile-section-heading"><p className="eyebrow">Feature breakdown</p><h2>Compare access.</h2></div>
      <div className="membership-table-wrap"><table className="membership-table">
        <thead><tr><th>Feature</th>{plans.map((plan) => <th key={plan.name}>{plan.name}</th>)}</tr></thead>
        <tbody>{features.map((feature) => <tr key={feature.name}>
          <th scope="row">{feature.name}</th>
          {feature.values.map((value, index) => <td key={`${feature.name}-${plans[index].name}`}>{value === 'Included' ? <span className="membership-included"><Check size={15} /> Included</span> : value}</td>)}
        </tr>)}</tbody>
      </table></div>
      <p className="membership-disclaimer">Paid prices and features are proposals only. Availability, plan terms, and payment approval must be confirmed before enrollment opens. No result or profit is promised.</p>
    </section>
  </main>
}