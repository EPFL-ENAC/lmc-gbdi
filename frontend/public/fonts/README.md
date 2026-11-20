# GBDI fonts

Fonts load from `src/css/00-fonts/fonts.css`; nothing is required here.

- **Satoshi** comes from Fontshare's hosted CSS. Its ITF Free Font EULA
  allows commercial use but not re-hosting the files publicly, so do NOT
  commit Satoshi files to this (public) repository.
- **SK Modernist** loads the file gbdi.io serves. Today `fonts.css` loads
  only that file. Once GBDI confirms the web licence, put
  `Sk-Modernist-Regular.woff2` here. Then add
  `url('/fonts/Sk-Modernist-Regular.woff2')` back as the first source in
  `fonts.css`.

Neither family is on Google Fonts.
