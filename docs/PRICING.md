# Pricing

The prices below are **samples the owner will adjust**. The real ones come from the platform admin through the public plans endpoint (`API-HOOKS.md`), so the site never hard-codes them. Show them in USD; other currencies come later with the payment processor (Payoneer).

## Periods

A toggle with **Monthly · Quarterly · Annually**:
- quarterly is **10% off** the monthly price;
- annually is **20% off**;
- amounts are rounded to whole cents.

The big number on each card is the **price per month** for the chosen period, and under it "billed €X every 3 months / every year". The saving shows as a small badge ("Save 20%").

| Plan | Monthly | Quarterly (whole period) | Annually (whole period) | Per month on annual |
|---|---|---|---|---|
| **Starter** | $0 | $0 | $0 | Free forever |
| **Professional** ("Most popular") | $19 | $51.30 | $182.40 | $15.20 |
| **Business** | $49 | $132.30 | $470.40 | $39.20 |
| **Enterprise** | Contact us | | | |

## Who each plan is for (copy from the app)

- **Starter:** individuals, students and hobbyists collecting data on a small scale or trying out the API. "Every core feature, free for as long as you like."
- **Professional:** startups and small teams that rely on regular, automated data and near real-time monitoring as they grow. "Everything in Starter, plus your own domain, sending address and company sign-in."
- **Business:** established companies with heavy data intake, advanced filtering and fast extraction. No limits. "Everything in Professional, with no limits on forms, responses or databases."
- **Enterprise:** large organisations with specific data requirements, strict security and compliance needs, or dedicated infrastructure. "Everything in Business, shaped around your organisation, with a dedicated team."

## Limits

| | Starter | Professional | Business | Enterprise |
|---|---|---|---|---|
| Forms | 5 | 20 | Unlimited | Unlimited |
| Responses on each form | 10,000 | 200,000 | Unlimited | Unlimited |
| Your own database | MySQL | MySQL, PostgreSQL, MariaDB | All five | All five |
| Sign-in with Google, Apple, Microsoft, Facebook | – | ✓ | ✓ | ✓ |
| Single sign-on (Okta and others) | – | ✓ | ✓ | ✓ |
| Custom domains | – | 1 | Unlimited | Unlimited |
| Own sending address and mail server | – | ✓ | ✓ | ✓ |
| AI credits a month | 100 | 500 | 2,000 | Custom |
| Languages | 20 | 20 | 20 | 20 |
| Data kept in the region you choose | – | – | – | ✓ |

## Comparison table rows (grouped as in the app's Settings → Plans)

1. **Forms and responses:** Forms · Responses on each form · Languages · Template repository · Custom lists · Themes and landing pages · Version history · Workspace and folders · Fill in later (continue where you stopped).
2. **Insight:** Advanced analytics · Visits and responses analytics · AI assistant.
3. **Your data:** Bring your database (one row per engine) · Database explorer · Live query editor · Data destinations.
4. **API service:** API service, endpoints, tokens and access rules · Webhooks · API documentation.
5. **Brand and address:** Branding · Formalie subdomain · Custom domain · Own sending address and mail server · Data kept in the region you choose.
6. **Sign-in:** Email and password · Google, Apple, Microsoft, Facebook · Single sign-on (Okta and others).
7. **Support:** Help centre and assistant · Priority email support (Professional and up) · Dedicated account team (Enterprise) · Security and compliance review (Enterprise).

## Buttons

- **Starter:** "Start free", which opens the portal sign-up with `?plan=starter`.
- **Professional and Business:** "Start with {plan}", which opens the portal sign-up with `?plan={id}&period={period}`. Checkout happens in the portal after the workspace is created (`SIGNUP-FLOW.md`).
- **Enterprise:** "Contact us", which goes to `/enterprise#enquiry` (the embedded Enterprise form, with the chosen period passed along).

## Pricing FAQ (starting set)

- Can I change plans later? Yes, any time: upgrades start at once, downgrades at the end of the paid period.
- What happens over a limit? Nothing is deleted. You can't add more until you upgrade.
- Do you offer discounts for non-profits and education? Contact us.
- Which payment methods? Cards and local methods through Payoneer. Enterprise can pay by invoice.
- Is my data mine? Yes. Export it any time, or keep it in your own database from day one.
