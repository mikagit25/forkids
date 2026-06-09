/**
 * Injects @font-face CSS for Noto Sans Arabic and Noto Kufi Arabic.
 * Fonts are bundled in public/fonts/ so they load offline during render.
 * Import this component once in any composition that uses Arabic text.
 */
import React from "react";
import { staticFile } from "remotion";

const CSS = `
@font-face {
  font-family: 'Noto Sans Arabic';
  font-weight: 900;
  font-style: normal;
  src: url('${staticFile("fonts/NotoSansArabic-Bold.ttf")}') format('truetype');
}
@font-face {
  font-family: 'Noto Sans Arabic';
  font-weight: 400;
  font-style: normal;
  src: url('${staticFile("fonts/NotoSansArabic-Regular.ttf")}') format('truetype');
}
@font-face {
  font-family: 'Noto Kufi Arabic';
  font-weight: 700;
  font-style: normal;
  src: url('${staticFile("fonts/NotoKufiArabic-Bold.ttf")}') format('truetype');
}
@font-face {
  font-family: 'Noto Kufi Arabic';
  font-weight: 400;
  font-style: normal;
  src: url('${staticFile("fonts/NotoKufiArabic-Regular.ttf")}') format('truetype');
}
`;

export const ArabicFonts: React.FC = () => (
  <style dangerouslySetInnerHTML={{ __html: CSS }} />
);
