import { PteClient } from './pte-client.mjs';

// loadAttempt must fetch prompts, answer keys, and acoustic evidence from your DB.
// Mount AFTER your authentication middleware; authorize the attempt's ownership.
export function mountPteRoutes(app, { loadAttempt, client = new PteClient() }) {
  app.post('/api/pte/attempts/:id/score', async (req, res, next) => {
    try {
      const attempt = await loadAttempt(req.params.id, req.user);
      if (!attempt) return res.status(404).json({ error: 'Attempt not found' });
      res.json(await client.scoreAttempt(attempt));
    } catch (error) { next(error); }
  });
}
