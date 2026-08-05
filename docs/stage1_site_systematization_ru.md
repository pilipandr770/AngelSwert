# AngelSwert - Stage 1 (Website Only) Systematization

## 1) Scope for Current Stage
Goal of Stage 1: launch only the marketing website with clear offers and conversion flow.

Included in Stage 1:
- Public website pages
- Brand-aligned visual design
- Service/program presentation
- Contact and lead capture points
- Blog as SEO section
- Basic AI chatbot on public site

Excluded from Stage 1 (keep in codebase, do not prioritize in UX now):
- Internal platform workflows
- Advanced CRM automation scenarios
- Deep admin analytics

## 2) Current Site Map in Project
Current public routes are already present:
- / (home)
- /about
- /services
- /programs
- /contact
- /blog
- /blog/{slug}

This map is enough for the first commercial launch.

## 3) Recommended Navigation (Top Menu)
Keep top menu concise for conversion:
- Home
- About
- Services
- Programs
- Blog
- Contact

Admin login should not be visible in public navigation in production mode.

## 4) Page-by-Page Block Structure

### Home (/)
Suggested order:
1. Hero section with core promise and CTA button
2. Brand proof block (who this is for + short credibility)
3. Services preview (3 cards)
4. Programs preview (2-3 offers with outcomes)
5. YouTube block (4 channels/cards)
6. Testimonials/case snippets
7. Final CTA (book call / contact)

### About (/about)
Suggested order:
1. Founder/brand story
2. Method and values
3. Why this approach works
4. CTA to consultation

### Services (/services)
Suggested order:
1. Services overview
2. Detailed service cards
3. Process: how collaboration works (3-5 steps)
4. FAQ mini-block
5. CTA

### Programs (/programs)
Suggested order:
1. Program lineup (tiers/packages)
2. Each program: for whom, format, result, duration
3. Optional comparison table
4. CTA per program

### Contact (/contact)
Suggested order:
1. Main contact methods
2. Preferred response time
3. Contact form / call booking action
4. Legal/basic footer details

### Blog (/blog and /blog/{slug})
Suggested order:
1. Blog index with SEO-focused categories/tags
2. Each article with:
   - H1 title
   - excerpt
   - readable structure (H2/H3)
   - CTA at end
3. Internal linking to services/programs

## 5) Content Inventory Template (Fill from Client Discovery)
Use this checklist when placing content from client material:
- Brand statement (1 sentence)
- Core audience (1-2 ICP profiles)
- Top pain points (3-5)
- Main outcomes (3-5)
- Services list with short and full descriptions
- Programs with price model or "request pricing"
- Social proof: testimonials, cases, metrics
- FAQ answers
- Contact channels and response policy

## 6) Design Direction from Shared Visual Sample
Visual sample indicates:
- Premium dark base + warm gold accents
- Strong emblem/logo presence
- Calm, high-trust tone

Suggested tokens for next iteration:
- Background dark slate: #4b5664
- Surface dark: #3f4956
- Gold primary: #c4a25b
- Gold light: #e4cc84
- Text on dark: #f3ecdc
- Muted text: #b9b4a8

Typography direction:
- Elegant serif for headings
- Clean readable sans-serif for body text

## 7) Priority Backlog (Execution Order)
P0 (do now):
- Replace placeholder texts with real client copy
- Rebuild home page blocks in conversion order
- Align colors/typography with logo sample
- Hide admin link from public header

P1:
- Add testimonials/case components
- Add contact form with lead capture
- Improve blog card metadata and internal links

P2:
- Add multilingual switch if needed (EN/DE/RU)
- Add schema.org markup for SEO
- Add performance pass (image optimization, lighthouse)

## 8) Acceptance Criteria for Stage 1
Stage 1 is complete when:
- Every public page has final approved copy
- Visual style follows logo direction consistently
- Clear CTA exists on each page
- Blog is publish-ready and SEO-structured
- Mobile and desktop layouts are both validated

## 9) Important Note About Attached Discovery File
The attached DOCX is not yet physically available in the workspace filesystem, so its full text could not be auto-parsed by tools.

To fully map "what text goes where", place the file into this repository (for example: ./docs/input/Angel_Swert_ASAI_Client_Discovery_EN_clean.docx), and it can be converted into a precise content-to-block matrix in the next pass.
