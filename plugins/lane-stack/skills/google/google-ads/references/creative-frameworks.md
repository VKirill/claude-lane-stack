# Creative Frameworks — как писать под Google Ads

Принципы написания headlines / descriptions с учётом RSA-логики динамической сборки + проверенные frameworks 4U / AIDA / PAS / FAB.

## RSA-логика — самое важное чтобы понять

RSA — **не один баннер**. Это **набор assets** из которого Google собирает разные комбинации для разных пользователей.

```
Pool: 12 headlines + 4 descriptions

User A видит: H[3] + H[7] + H[11] | D[1] + D[2]
User B видит: H[1] + H[5] + H[9]  | D[3] + D[4]
User C видит: H[2] + H[3] + H[12] | D[1] + D[4]
...
```

Google решает по machine learning какая комбинация даст лучший CTR для конкретного запроса/пользователя. Поэтому:

1. **Каждый headline должен звучать как самостоятельная фраза.**
   ❌ "Best Italian" + "Restaurant in NYC" (зависят от порядка)
   ✓ "Authentic Italian in NYC" + "Family-Owned Since 1962" (каждый самодостаточен)

2. **Diversity > Repetition.** Разные angles в разных headlines:
   - Cost: "From $9/mo" / "Free 30-Day Trial"
   - Time: "24/7 Support" / "Same-Day Shipping"
   - Trust: "5-Star Rated" / "500K+ Customers" / "BBB Accredited"
   - Outcome: "Save Time" / "Boost Sales 3x" / "No More Spam"
   - USP: "Made in USA" / "Eco-Friendly" / "Patented Tech"
   - Audience: "For Small Business" / "Built for Marketers"
   - CTA: "Get a Quote" / "Book a Demo" / "Shop the Sale"

3. **Pinning минимально.** Закрепляешь headline на позицию 1/2/3 только когда **юридически обязан** или брендовая дисциплина того требует. Pinning режет диверсификацию → режет Quality Score.

   Pinning OK когда:
   - Регистрационный номер брокера должен быть видим (финуслуги)
   - Brand disclaimer обязателен
   - Лицензия здравоохранения должна быть в первом headline

   Pinning NOT OK когда:
   - "Я хочу чтобы 'Best Deal' всегда был первым" — это потеря optimization
   - "У меня самый сильный headline" — Google знает лучше через A/B

4. **Включай keyword в 2-3 headlines, не во все.**
   Если key = "buy iphone case":
   - H1: "Premium iPhone Cases" — yes keyword
   - H2: "Buy iPhone Cases Online" — yes keyword
   - H3: "Shop Now — Free Shipping" — no keyword, CTA
   - H4: "5-Star Rated by 100K+" — no keyword, trust
   - H5: "Made for iPhone 15 Pro Max" — yes keyword variant
   - H6: "Same-Day Shipping" — no keyword, USP
   - H7-H12: разные angles без keyword

   Google помечает "keyword stuffing" если ВСЕ headlines содержат keyword.

---

## Headline frameworks — конкретные шаблоны

### 4U (Useful / Urgent / Unique / Ultra-Specific)

Каждый headline должен иметь минимум 2 из 4 U:

| Слабый | Сильный (с U-маркерами) |
|---|---|
| "Italian Restaurant" | "Authentic Italian — Family-Owned" (Useful + Unique) |
| "Pizza Delivery" | "30-Min Pizza Delivery in Brooklyn" (Urgent + Ultra-Specific) |
| "Online Course" | "Master SQL in 30 Days — $99" (Useful + Urgent + Ultra-Specific) |

### AIDA — split по headlines

В одном RSA-ad можешь распределить AIDA по разным headlines:

- **Attention** (Hook): H1, H2 — keyword-rich, intriguing
- **Interest** (USP): H3, H4 — benefits, USP, social proof
- **Desire** (Why now): H5, H6 — urgency, offer
- **Action** (CTA): H7, H8 — "Get Started", "Buy Now", "Book Demo"

### PAS (Problem-Agitate-Solve) — для descriptions

Descriptions имеют 90 символов — хватит на один шаг PAS:

- **Description 1**: Problem + Solution → "Tired of slow CRMs? Our platform loads in 200ms. Try free for 14 days."
- **Description 2**: Agitate + Differentiator → "Lost leads = lost revenue. 10,000+ teams trust our tool to never miss a follow-up."

### FAB (Features-Advantages-Benefits)

Distribute across headlines:
- **Feature**: "256-bit encryption", "API access included"
- **Advantage**: "Bank-grade security", "Build custom integrations"
- **Benefit**: "Sleep at night knowing data is safe", "Save 20 hours/week"

Лучше всего работает Benefit > Advantage > Feature. Но клиенты часто пишут feature-only — твоя работа подтянуть до benefit.

---

## Descriptions — расширяй ценность, не повторяй headline

### Структура хорошего description (90 символов)

```
[Benefit / Hook] [Key proof / specific] [Soft CTA].
```

Примеры:

- "Cut your invoicing time in half. 50,000+ small businesses already do. Try free."
- "Shop the entire SS26 collection — designed in Milan, made by hand in Florence."
- "Get a custom B2B quote in 24 hours. No subscriptions, no hidden fees, ever."

### Antipatterns

❌ "We are the best provider of high-quality services in our industry."  (vague, no benefit, no proof)

❌ "Click here now! Buy today!! Best deal ever!!!"  (excessive punctuation = automatic disapproval)

❌ "Get free CRM access $0 trial unlimited users no credit card."  (run-on, no commas, no clarity)

❌ Description = повторение headline в других словах (Google помечает)

---

## Trust / Social Proof — что работает

Google Ads CTR boost'еры (по приоритету):

1. **Numbers**: "10,000 customers", "5 million downloads", "Rated 4.9/5 (12,000 reviews)"
2. **Time**: "Founded 1962", "30 years experience", "Trusted since 2010"
3. **Authority**: "Featured in Forbes", "BBB Accredited", "ISO 27001 Certified"
4. **Specificity**: "Built for Fortune 500", "Used by 8 of top 10 banks"
5. **Guarantee**: "30-day money back", "Lifetime support", "No questions asked"

❌ "Best", "leading", "top", "#1" без обоснования — Google помечает как unsupported claims при автоаудите. Если используешь — подтверждай в landing page и/или в самом description.

---

## CTA (Call to Action) — варианты

Слабые CTA → не кликаются. Сильные CTA → задают action:

### Weak CTAs (избегать)
- "Click Here"
- "Learn More"
- "Visit Site"

### Strong CTAs (использовать)
- Discovery-stage: "See How It Works", "Watch 2-Min Demo", "Read the Guide"
- Consideration: "Compare Plans", "Get a Custom Quote", "Take Free Assessment"
- Action: "Start Free Trial", "Buy Now & Save 20%", "Book a 15-Min Call"
- Lower-funnel: "Order in 60 Sec", "Get Quote Instantly", "Reserve Your Spot"

### Match CTA to bottom-of-funnel stage

- TOF (Top-of-Funnel) → "Learn", "Read", "See"
- MOF (Mid-of-Funnel) → "Compare", "Estimate", "Calculate"
- BOF (Bottom-of-Funnel) → "Buy", "Book", "Order", "Subscribe"

---

## RSA Final Examples — полные

### Example 1: B2B SaaS (CRM)

```yaml
format: RSA
headlines:
  - "B2B CRM for Modern Teams"          # 23 chars — keyword + audience
  - "10x Your Pipeline in 90 Days"      # 28 — benefit + time
  - "Track Every Lead Effortlessly"     # 29 — benefit
  - "Used by 8 Fortune 500 Brands"      # 28 — social proof
  - "Free 14-Day Trial, No Card"        # 26 — offer
  - "AI-Powered Lead Scoring"           # 23 — USP feature
  - "GDPR + SOC 2 Compliant"            # 22 — compliance
  - "Setup in 5 Minutes"                # 18 — speed
  - "$29/mo Per User"                   # 15 — price
  - "Replace Salesforce in a Day"       # 27 — competitive
  - "200K+ Sales Pros Trust Us"         # 25 — social proof
  - "Book a 15-Min Demo"                # 18 — CTA

descriptions:
  - "AI-driven CRM that finds & scores leads automatically. Free 14-day trial. No card."   # 88
  - "Built for B2B sales teams. Real-time pipeline visibility. SOC 2 + GDPR compliant."     # 86
  - "Trusted by 200K+ sales pros worldwide. Setup in 5 minutes — replace Salesforce now."   # 90
  - "From $29/user/month. Free migration. 24/7 customer support. Book a demo today."        # 84
```

Total = 12 headlines + 4 descriptions. Ad strength = Excellent likely.

### Example 2: E-commerce (DTC fashion)

```yaml
format: RSA
headlines:
  - "Italian Linen Shirts"
  - "Hand-Stitched in Florence"
  - "Sustainable & Premium"
  - "Free Shipping Over $100"
  - "30-Day Easy Returns"
  - "Spring Collection 2026"
  - "Sizes XS-3XL Available"
  - "Featured in Vogue"
  - "5-Star Rated by 50K+"
  - "Shop the New Drop"
  - "Up to 40% Off Spring Sale"
  - "Made for Conscious Closets"

descriptions:
  - "Premium Italian linen shirts handmade in Florence. Free shipping over $100."
  - "Sustainable, season-less, sized inclusively (XS-3XL). 30-day easy returns."
  - "Featured in Vogue, Forbes, NYT. Rated 5★ by 50K+ customers worldwide."
  - "Shop the Spring 2026 collection. Up to 40% off through Sunday only."
```

---

## Pinning — когда и как

Если **юридически обязан** закрепить headline:

```yaml
headlines:
  - text: "Licensed Insurance Provider"
    pinned: 1  # always position 1
  - text: "Get a Quote in 5 Minutes"
    pinned: null
  - text: "Save 20% on Auto Insurance"
    pinned: null
  ...
```

Если **legally required**, pin минимум возможного:
- 1 headline на position 1 — OK
- 1 description на position 1 — OK
- Пиннить >2 = убивает RSA logic

---

## Ad Strength rating — что значит

Google показывает в редакторе:
- **Excellent** — 8+ headlines, 4 descriptions, разнообразие, нет дублей
- **Good** — 5+ headlines, 3+ descriptions
- **Average** — минимум 3 headlines, 2 descriptions, но без diversity
- **Poor** — много дублей, мало assets, всё запиннено

Excellent → +12% conversions vs Poor (Google's own statistics).

Цель: **Excellent или Good**. Average — критический минимум.

---

## Финальный чек-лист перед сдачей RSA

- [ ] 8-12 headlines (минимум — 5)
- [ ] 3-4 descriptions (минимум — 3)
- [ ] Каждый headline = самостоятельная фраза, не "продолжение"
- [ ] Diversity: разные angles (cost, time, trust, outcome, USP, CTA)
- [ ] Keyword в 2-3 headlines, не во всех
- [ ] CTA в 1-2 headlines (action verbs)
- [ ] Social proof / numbers в 1-2 headlines
- [ ] Pinning только для legal обязательств
- [ ] Прогон через `scripts/validate-ads.py` — все pass
- [ ] Ad Strength в Google Ads = Excellent / Good (не Average / Poor)
- [ ] Landing page подтверждает оффер каждого headline (квалификация Quality Score)
- [ ] UTM-разметка на Final URL для tracking

См. также: [pre-launch-checklist.md](pre-launch-checklist.md) для полного pre-launch.
