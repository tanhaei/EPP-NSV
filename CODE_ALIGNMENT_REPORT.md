# گزارش هم‌راستاسازی کد با مقاله V2

## مبنا و محدوده

این بررسی با **`paper/V2.tex`** و **`paper/bibliography.bib`** موجود در سورس نهایی انجام شد. فایل مقاله‌ی قدیمی به `paper/archive/V1.tex` منتقل شده و نسخه‌ی اجرایی/مستندی مخزن اکنون V2 است.

این مخزن یک **prototype و benchmark مصنوعی** است. هیچ داده‌ی بیمار، یادداشت بالینی، تصویر، cohort، یا نتیجه‌ی BioArc در آن قرار نگرفته و خروجی تست‌ها نباید به‌عنوان دقت بالینی، ایمنی بالینی، توافق پزشکان یا عملکرد روی داده‌ی واقعی تفسیر شود.

> **محدودیت کنترل نسخه:** ZIP ارسالی شامل تاریخچه یا شیء `.git` قابل‌اعتبارسنجی نبود. بنابراین `code_commit` در manifest اجرای نمونه با مقدار `unavailable_in_source_archive` ثبت شده است. برای تشخیص دقیق همین درخت منبع، SHA-256 آن برابر است با: `b7309ccbda5461136865cfeb1d89eed6d81b7892ab0cfa81b5d378bbe7e3cceb`.

## اصلاحات انجام‌شده

| الزام مقاله V2 | وضعیت قبلی | اصلاح اعمال‌شده |
|---|---|---|
| منبع مقاله | سورس فعال هنوز `V1.tex` بود. | `V2.tex` و BibTeX فعلی در `paper/` مرجع رسمی مخزن شدند؛ V1 فقط در archive نگه‌داری شد. |
| بردار تصمیم | خروجی‌ها حالت درمانی/بالینیِ غیرهمسو داشتند. | `DecisionVector` فقط شامل `scope_status`، `management_tier`، `review_urgency_tier` و `evidence_status` است. |
| مدل episode و شواهد | فیلدهای V2 برای laterality، زمان، provenance، assertion، validation و missingness کامل نبودند. | مدل `PatientEyeEpisode`، نرمال‌سازی CSV، semantic lifting و evidence graph بازطراحی شدند. |
| درمان ثبت‌شده | امکان درآمیختن token درمان ثبت‌شده با منطق policy وجود داشت. | `recorded_treatment_token` و زمان آن در مدل نگه‌داری می‌شوند، اما صراحتاً از observation model و امضای policy خارج هستند. |
| laterality و scope | laterality نامشخص به‌صورت نادرست out-of-scope می‌شد. | laterality نامشخص به `Indeterminate` می‌رسد؛ disease/competing pathology و mismatch چشم، gate جداگانه‌ی scope دارند. |
| محافظه‌کاری شواهد | عمر مشاهده، provenance و validation به‌شکل کامل enforce نمی‌شدند. | guardهای temporal، missingness، provenance و validation پیش از تصمیم اعمال و در audit ثبت می‌شوند. |
| SMT و audit | trace برای دلیل تمایز و counterexample کامل نبود. | verifier اکنون verdict، علت‌ها، solver status، facts پذیرفته/ردشده، scope trace، policy hash و counterexample را در audit ثبت می‌کند. |
| taxonomy مصنوعی | خانواده‌های V2 کامل نبودند. | ۸ خانواده افزوده شد: demographic shift، near miss، cross-eye، missing critical evidence، stale/post-index، treatment-token trap، contradictory evidence و policy-version perturbation. |
| reproducibility bundle | manifest و bundle فاقد چند artifact ضروری V2 بودند. | `fixture_manifest.json`، `policy_manifest.json`، prediction، audit، metrics، ablation، policy-version comparison، environment، dependency-lock hash، report، جدول LaTeX و hashهای artifact تولید می‌شوند. |
| controlled harness | policy خصوصی ناقص ممکن بود دیر و مبهم شکست بخورد. | قرارداد factory سخت‌گیرانه شد؛ policy ناقص پیش از اجرای controlled study رد می‌شود و audit/manifest کنترل‌شده تولید می‌شود. |
| CI و مستندات | smoke و CI روی تعداد قدیمی ۶۰ fixture بودند. | Makefile، GitHub Actions، smoke script و مستندات روی seed ثابت و ۶۴ fixture V2 هم‌راستا شدند. |

## آزمون‌های اجراشده

| آزمون | نتیجه |
|---|---|
| `python -m pip check` | Pass — وابستگی شکسته‌ای گزارش نشد. |
| `python -m compileall -q src tests` | Pass |
| `python -m pytest -q` | **16 passed** |
| `make smoke` | Pass — ۶۴ fixture با seed `17` تولید شد. |
| integrity check برای bundle | Pass — ۱۲ artifact موردنیاز وجود دارند و SHA-256 تک‌تک با `run_manifest.json` یکسان است. |
| build package | Pass — wheel `epp_nsv_bioarc-0.3.0-py3-none-any.whl` ساخته شد. |

## نتیجه اجرای بازتولیدپذیر

- تعداد pairها: **64**
- خانواده‌های fixture: **8**
- انطباق کامل verifier با oracle مصنوعی: **100%**
- equivalence ناایمن در fixtureهای guard: **0**
- policy: `DEMO-DRDME-v1`
- policy hash: `f7bbe4a6a8c3f183b163d71dd8e9aec31b54ae433b36d59a280c12ca2cb7239c`
- تفسیر مجاز: **فقط اعتبارسنجی نرم‌افزاری مصنوعی**

## فایل‌های تحویلی

- `epp_nsv_v2_aligned_source.zip`: سورس اصلاح‌شده، مقاله V2، BibTeX، تست‌ها، مستندات و CI؛ بدون محیط مجازی و خروجی‌های موقت.
- `epp_nsv_v2_final_run_bundle.zip`: خروجی کامل اجرای seed ثابت شامل fixtureها، auditها، manifestها، metricها و artifact hashها.
