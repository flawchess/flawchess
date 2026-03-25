import { renderToString } from 'react-dom/server';
import { StaticRouter } from 'react-router-dom';
import { Routes, Route } from 'react-router-dom';
import { HomePageContent } from './pages/Home';
import { PrivacyPage } from './pages/Privacy';

export async function prerender(data: { url: string }) {
  const html = renderToString(
    <StaticRouter location={data.url}>
      <Routes>
        <Route path="/" element={<HomePageContent />} />
        <Route path="/privacy" element={<PrivacyPage />} />
      </Routes>
    </StaticRouter>
  );
  return { html };
}
