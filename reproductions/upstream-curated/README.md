# Official curated video source pack

Этот каталог создаётся из pinned production bundle официального сайта Hy-Nomas:

`https://hy-nomas.hy.tencent.com/assets/index-DdHuI7-l.js`

Обновить/проверить файлы:

```bash
make upstream-sources
make upstream-sources-check
```

В каждом каталоге находятся неизменённая публичная Gallery-запись, provenance,
статус доступности и сведения о camera-control. `scenario.json` существует
только там, где upstream опубликовал полный text-only timeline. Это адаптер
публичного timeline к локальному формату, а не найденный upstream scenario-файл.

Полностью опубликованы и пригодны для одинакового CLI/Web structured JSON replay:

- `snow-palace-ascent`
- `voxel-adventure`
- `kitchen-stories`

Неполны и намеренно не имеют `scenario.json`:

- `snow-palace-walk` — скрыты prompts 1, 3, 4 и camera trajectory сегмента 2;
- `coastal-waterfall` — скрыта camera trajectory сегмента 3;
- `street-coffee` — скрыты prompts 4 и 5.

Для Web откройте `web-replay.json`: создайте world с полями `setup`, затем
вставьте содержимое `scenario` одним JSON в поле direction. UI распознает
structured SegAR JSON и не пропустит его через prompt enhancer.
