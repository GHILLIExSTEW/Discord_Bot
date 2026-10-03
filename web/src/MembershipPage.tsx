import { ArrowRight, Check } from 'lucide-react'
import { Link } from 'react-router-dom'

const plans = [
  { name: 'ALL-STAR', price: '$9.99', summary: 'ALL-STAR Discord access, with an optional free seven-day trial. The trial expires without a charge and does not include Member Vault submissions.', featured: false },
  { name: 'HIGHROLLER', price: '$29.99', summary: 'HIGHROLLER Discord access. Paid-only; no free trial. Review included channels and benefits before purchasing.', featured: true },
]

const prepaidOffers = [
  { term: '1 month', days: 30, discount: '0%', gold: '$9.99', platinum: '$29.99' },
  { term: '3 months', days: 90, discount: '5%', gold: '$28.47', platinum: '$85.47' },
  { term: '6 months', days: 180, discount: '10%', gold: '$53.95', platinum: '$161.95' },
  { term: '12 months', days: 365, discount: '15%', gold: '$101.90', platinum: '$305.90' },
]

const features = [
  { name: 'Public settled-play record', values: ['Included', 'Included'] },
  { name: 'Personalized sports & capper follows', values: ['Included', 'Included'] },
  { name: 'Weekly recap', values: ['Included', 'Included'] },
  { name: 'Tier Discord access', values: ['ALL-STAR channels', 'HIGHROLLER channels'] },
  { name: 'Free trial', values: ['7 days; no automatic charge', 'Not offered'] },
  { name: 'Member Bet Vault submissions', values: ['Verified paid access only; no trial submissions', 'Verified paid access required'] },
]

export default function MembershipPage() {
  return <section className="membership-page">
    <Link to="/" className="capper-back-link"><ArrowRight size={16} /> Home</Link>
    <header className="membership-page-heading">
      <p className="eyebrow">Membership</p>
      <h1>Find your seat.</h1>
      <p>Compare Playmaker Picks prepaid memberships. For adults 21+ (or the higher local legal age). Checkout remains closed while launch review is completed.</p>
    </header>
    <section className="membership-plan-grid" aria-label="Membership plans awaiting launch">
      {plans.map((plan) => <article className={`membership-plan${plan.featured ? ' is-featured' : ''}`} key={plan.name}>
        <p className="eyebrow">{plan.featured ? 'Full card' : 'Playmaker Picks'}</p>
        <h2>{plan.name}</h2>
        <p className="membership-price">{plan.price}<span> / 30 days prepaid</span></p>
        <p>{plan.summary}</p>
        <a className="button membership-interest" href={`mailto:support@playmakersportsanalytics.com?subject=${encodeURIComponent(`Playmaker ${plan.name} membership interest`)}`}>Get launch updates <ArrowRight size={16} /></a>
      </article>)}
    </section>
    <section className="membership-breakdown" aria-label="Prepaid prices">
      <div className="profile-section-heading"><p className="eyebrow">Pay upfront</p><h2>Choose your access duration.</h2></div>
      <div className="membership-table-wrap"><table className="membership-table">
        <thead><tr><th scope="col">Offer</th><th scope="col">Exact duration</th><th scope="col">Discount</th><th scope="col">ALL-STAR total (USD)</th><th scope="col">HIGHROLLER total (USD)</th></tr></thead>
        <tbody>{prepaidOffers.map((offer) => <tr key={offer.days}><th scope="row">{offer.term}</th><td>{offer.days} days</td><td>{offer.discount}</td><td>{offer.gold}</td><td>{offer.platinum}</td></tr>)}</tbody>
      </table></div>
      <p className="membership-disclaimer">One-time payments, no automatic renewal. Month labels mean the exact days shown, not calendar months. Discounts are against 3, 6, or 12 purchases at the 30-day base price, rounded once to cents. Any taxes or checkout fees must be disclosed before payment.</p>
      <p className="membership-disclaimer">Read the draft <Link to="/terms">Terms</Link>, <Link to="/privacy">Privacy notice</Link>, and <Link to="/refunds">Refund policy</Link>. Refund requests for access failures or duplicate charges should be made within seven days; losing picks do not qualify by themselves. Applicable legal rights and Whop rules still apply.</p>
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
      <p className="membership-disclaimer">Tier benefits, role mappings, policies, and payment approval must be confirmed before enrollment opens. PLAYMAKER is the capper role, not a membership tier. No result, daily pick count, or profit is promised.</p>
    </section>
  </section>
}