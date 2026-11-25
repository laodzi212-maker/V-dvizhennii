# Набор «рилсы и автоматизация» (25.11.2026)
1. facts/check_facts.py файл — сверка с facts.json. Коды: 0 чисто, 1 ошибки (не публиковать), 2 нужны решения Никиты.
2. reels/build_route.py — анимация маршрута из facts.json; рендер: npx hyperframes render -q draft (нужен Chrome).
3. subs/transcribe.py голос.wav out/имя — субтитры SRT/ASS (pip install sherpa-onnx, модель GigaAM v2); вшивание: ffmpeg -vf ass=имя.ass.
   Голос в тесте синтетический (piper), в реальных рилсах — голос Никиты.
4. atlantum/index.html — окно управления (артефакт).
Порядок для рилса: текст -> check_facts -> рендер -> субтитры -> check_facts по SRT -> одобрение -> публикация.
