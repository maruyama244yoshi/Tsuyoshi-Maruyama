# 口パク動画の元になる高解像度の基本画像（プロンプト）

各プロンプトは `tools/akari_news/prompt_builder.py` が定義ファイルから生成したもの。reference の画像を**画像参照**として必ず併用する。

## AKARI_BASE_A_16x9（16:9）

- 参照画像：`brand/akari/references/cuts/AKARI_REF001_CAM01_front.png`

```
Japanese female AI news anchor named Akari, late twenties to early thirties appearance, elegant and intelligent, warm and trustworthy, polished but approachable, natural Japanese facial features, refined beauty without looking like a fashion model or idol, calm confident presence, professional real-estate and financial news presenter, realistic human appearance, consistent identity across all images. Face: soft oval face, balanced facial proportions, gentle intelligent eyes, natural dark brown eyes, subtle double eyelids, straight natural eyebrows, small refined nose, natural soft lips, warm subtle smile, clear natural skin, realistic skin texture, no excessive retouching. Hair: dark brown semi-long hair, shoulder to upper-chest length, soft natural inward curl or very light wave, side-swept fringe, clean professional hairstyle, hair never covering the eyes. Makeup: natural professional news-anchor makeup, subtle eye makeup, soft pink-beige lip color, very light blush, understated and refined. Body: natural healthy slim-to-average build, realistic proportions, professional posture, relaxed shoulders, upright stance. Overall impression: intelligent, elegant, calm, sincere, reliable, warm, approachable, professional, premium Japanese economic-news presenter.

navy tailored blazer, clean white blouse, minimal delicate earrings, refined professional business attire

gentle calm smile, friendly attentive expression, relaxed professional confidence

medium close-up, chest-up framing, front-facing, eye-level camera, symmetrical professional news-anchor framing

premium modern Japanese real-estate news studio, sophisticated navy and white interior, subtle warm gold accents, large high-resolution display panels showing city skyline, apartment buildings, Japanese map, interest-rate charts and real-estate market graphs, elegant clean newsroom desk, cinematic but realistic studio lighting, warm accent lights, polished television-news atmosphere, minimalist luxury design, highly professional, uncluttered.

soft professional broadcast lighting, natural flattering key light, subtle fill light, warm rim light, realistic skin tones, no harsh shadows, premium television studio lighting, natural photographic realism

neutral closed mouth, looking straight into the camera, hands resting out of frame, high resolution 1920x1080 or larger, face clearly visible and evenly lit for talking-avatar animation
```

Negative / 制約：

```
Do not change identity. Do not change facial structure. Do not change ethnicity. Do not make her look younger than mid-twenties or older than mid-thirties. No anime style. No cartoon. No doll-like face. No excessive beauty filter. No plastic skin. No exaggerated large eyes. No heavy makeup. No red lipstick. No glamorous fashion-model styling. No idol styling. No nightlife styling. No revealing clothing. No cleavage emphasis. No exaggerated body proportions. No dramatic emotional expression. No shocked face. No clickbait expression. No futuristic sci-fi newsroom. No neon cyberpunk environment. No random accessories. No visible luxury-brand logos. No inconsistent hairstyle. No blonde hair. No short haircut.
```

## AKARI_BASE_E_9x16（9:16）

- 参照画像：`brand/akari/references/cuts/AKARI_REF001_CAM01_front.png`

```
Japanese female AI news anchor named Akari, late twenties to early thirties appearance, elegant and intelligent, warm and trustworthy, polished but approachable, natural Japanese facial features, refined beauty without looking like a fashion model or idol, calm confident presence, professional real-estate and financial news presenter, realistic human appearance, consistent identity across all images. Face: soft oval face, balanced facial proportions, gentle intelligent eyes, natural dark brown eyes, subtle double eyelids, straight natural eyebrows, small refined nose, natural soft lips, warm subtle smile, clear natural skin, realistic skin texture, no excessive retouching. Hair: dark brown semi-long hair, shoulder to upper-chest length, soft natural inward curl or very light wave, side-swept fringe, clean professional hairstyle, hair never covering the eyes. Makeup: natural professional news-anchor makeup, subtle eye makeup, soft pink-beige lip color, very light blush, understated and refined. Body: natural healthy slim-to-average build, realistic proportions, professional posture, relaxed shoulders, upright stance. Overall impression: intelligent, elegant, calm, sincere, reliable, warm, approachable, professional, premium Japanese economic-news presenter.

navy tailored blazer, clean white blouse, minimal delicate earrings, refined professional business attire

gentle calm smile, friendly attentive expression, relaxed professional confidence

medium close-up, chest-up framing, front-facing, eye-level camera, symmetrical professional news-anchor framing

premium modern Japanese real-estate news studio, sophisticated navy and white interior, subtle warm gold accents, large high-resolution display panels showing city skyline, apartment buildings, Japanese map, interest-rate charts and real-estate market graphs, elegant clean newsroom desk, cinematic but realistic studio lighting, warm accent lights, polished television-news atmosphere, minimalist luxury design, highly professional, uncluttered.

soft professional broadcast lighting, natural flattering key light, subtle fill light, warm rim light, realistic skin tones, no harsh shadows, premium television studio lighting, natural photographic realism

vertical 9:16 composition, head and shoulders in the upper half, neutral closed mouth, looking into the camera, high resolution 1080x1920 or larger
```

Negative / 制約：

```
Do not change identity. Do not change facial structure. Do not change ethnicity. Do not make her look younger than mid-twenties or older than mid-thirties. No anime style. No cartoon. No doll-like face. No excessive beauty filter. No plastic skin. No exaggerated large eyes. No heavy makeup. No red lipstick. No glamorous fashion-model styling. No idol styling. No nightlife styling. No revealing clothing. No cleavage emphasis. No exaggerated body proportions. No dramatic emotional expression. No shocked face. No clickbait expression. No futuristic sci-fi newsroom. No neon cyberpunk environment. No random accessories. No visible luxury-brand logos. No inconsistent hairstyle. No blonde hair. No short haircut.
```

## AKARI_BASE_B_desk（16:9）

- 参照画像：`brand/akari/references/cuts/AKARI_REF001_CAM03_desk.png`

```
Japanese female AI news anchor named Akari, late twenties to early thirties appearance, elegant and intelligent, warm and trustworthy, polished but approachable, natural Japanese facial features, refined beauty without looking like a fashion model or idol, calm confident presence, professional real-estate and financial news presenter, realistic human appearance, consistent identity across all images. Face: soft oval face, balanced facial proportions, gentle intelligent eyes, natural dark brown eyes, subtle double eyelids, straight natural eyebrows, small refined nose, natural soft lips, warm subtle smile, clear natural skin, realistic skin texture, no excessive retouching. Hair: dark brown semi-long hair, shoulder to upper-chest length, soft natural inward curl or very light wave, side-swept fringe, clean professional hairstyle, hair never covering the eyes. Makeup: natural professional news-anchor makeup, subtle eye makeup, soft pink-beige lip color, very light blush, understated and refined. Body: natural healthy slim-to-average build, realistic proportions, professional posture, relaxed shoulders, upright stance. Overall impression: intelligent, elegant, calm, sincere, reliable, warm, approachable, professional, premium Japanese economic-news presenter.

navy tailored blazer, clean white blouse, minimal delicate earrings, refined professional business attire

gentle calm smile, friendly attentive expression, relaxed professional confidence

seated behind modern news desk, medium shot, natural hand placement, professional broadcast framing

premium modern Japanese real-estate news studio, sophisticated navy and white interior, subtle warm gold accents, large high-resolution display panels showing city skyline, apartment buildings, Japanese map, interest-rate charts and real-estate market graphs, elegant clean newsroom desk, cinematic but realistic studio lighting, warm accent lights, polished television-news atmosphere, minimalist luxury design, highly professional, uncluttered.

soft professional broadcast lighting, natural flattering key light, subtle fill light, warm rim light, realistic skin tones, no harsh shadows, premium television studio lighting, natural photographic realism

neutral closed mouth, looking into the camera, high resolution
```

Negative / 制約：

```
Do not change identity. Do not change facial structure. Do not change ethnicity. Do not make her look younger than mid-twenties or older than mid-thirties. No anime style. No cartoon. No doll-like face. No excessive beauty filter. No plastic skin. No exaggerated large eyes. No heavy makeup. No red lipstick. No glamorous fashion-model styling. No idol styling. No nightlife styling. No revealing clothing. No cleavage emphasis. No exaggerated body proportions. No dramatic emotional expression. No shocked face. No clickbait expression. No futuristic sci-fi newsroom. No neon cyberpunk environment. No random accessories. No visible luxury-brand logos. No inconsistent hairstyle. No blonde hair. No short haircut.
```

## OOKA_M_BASE_A_16x9（16:9）

- 参照画像：`brand/ooka_m/references/cuts/OOKA_M_REF001_banner.png`

```
Japanese male AI commentator called Ooka M, fictional character, early to late forties appearance, calm, realistic, analytical, experienced real-estate investor and office worker, thin black-framed rectangular glasses, short neat black hair, clean-shaven, approachable practical demeanor, realistic human appearance, consistent identity across all images, fictional face not based on any real person.

navy tailored jacket over an open-collar shirt or a plain dark crew-neck inner, smart casual business style

calm composed expression, attentive, speaking naturally with modest hand gestures

medium shot, chest-up, slight angle, seated at a studio desk, eye-level camera

neutral modern news studio set matching the AKARI_STUDIO_01 navy and warm-wood palette, softly blurred city-night window, no identifiable real location, no company logos, no personal belongings

soft professional broadcast lighting, natural key light, subtle fill, realistic skin tones, no harsh shadows, natural photographic realism

neutral closed mouth, looking slightly off-camera toward an interviewer, high resolution 1920x1080 or larger, face clearly visible
```

Negative / 制約：

```
Do not change identity. Do not resemble any real person or celebrity. No anime style. No cartoon. No flashy clothing. No luxury-brand logos. No exaggerated gestures. No aggressive or salesman-like expression. No sunglasses. No beard change. No readable text in the image.
```
