-- Applied to production 2026-11-17. Additive, idempotent seed for canonical survey options and six traits.
INSERT INTO public.taste_traits (trait_name, description) VALUES
('physical','조작·피지컬'),
('strategy','전략·문제 해결'),
('exploration','탐색·수집'),
('emotion','감성·몰입'),
('comfort','휴식·힐링'),
('competition','경쟁·성취')
ON CONFLICT (trait_name) DO NOTHING;

INSERT INTO public.survey_options (question_id, option_text, option_order)
SELECT q.id, opt.value, (opt.ordinality - 1)::integer
FROM public.survey_questions q
CROSS JOIN LATERAL jsonb_array_elements_text(q.options)
  WITH ORDINALITY AS opt(value, ordinality)
WHERE q.track IN ('gamer','nongamer')
  AND q.stage IN ('onboarding','profile')
ON CONFLICT (question_id, option_order)
DO UPDATE SET option_text = EXCLUDED.option_text;
