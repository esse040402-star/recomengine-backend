import { useEffect, useState } from 'react';
import { ViewContext } from './state/ViewContext';
import usePageController from './hooks/usePageController';
import AppLayout from './components/layout/AppLayout';
import { resolveRoute } from './utils/routes';

function Page({ c }) {
  if (c.route.startsWith('survey/')) return c.survey(c.route.split('/')[1]);
  if (c.route.startsWith('game/')) return c.gamePage();

  const pages = {
    welcome: 'welcome',
    home: 'home',
    result: 'quickResult',
    'deep-intro': 'deepIntro',
    explore: 'exploreScreen',
    rankings: 'rankings',
    news: 'newsScreen',
    saved: 'savedGames',
    profile: 'profile',
    report: 'reportScreen'
  };

  return c[pages[c.route]]();
}

function EmailVerifiedScreen() {
  return (
    <section style={{
      minHeight: '80vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center',
      padding: '24px'
    }}>
      <p>
        인증이 완료되었습니다. 기존 페이지로 돌아가 회원가입을 완료해주세요.
      </p>
    </section>
  );
}

export default function App() {
  const c = usePageController();
  const [emailVerified, setEmailVerified] = useState(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const query = new URLSearchParams(window.location.search);

    const type = hash.get('type') || query.get('type');
    const errorCode = hash.get('error_code') || query.get('error_code');

    const token =
      hash.get('access_token') ||
      query.get('access_token') ||
      query.get('token_hash') ||
      query.get('code');

    // Supabase PKCE 이메일 인증은 ?code=... 형태로 돌아올 수 있다.
    // 이 경우 type=signup이 없어도 인증 완료 안내 화면을 표시한다.
    return (
      (type === 'signup' && !!token) ||
      !!query.get('code') ||
      errorCode === 'otp_expired'
    );
  });

  useEffect(() => {
    if (!emailVerified) return;

    window.history.replaceState(
      null,
      '',
      window.location.pathname
    );
  }, [emailVerified]);

  const target = resolveRoute(c.route, {
    state: c.state,
    user: c.accountUser,
    forceOnboarding: c.forceOnboarding,
    gameExists: c.game,
    firstGame: c.list()[0]?.id
  });

  useEffect(() => {
    if (!emailVerified && c.auth.ready && target !== c.route) {
      c.goto(target);
    }
  }, [target, c.route, c.auth.ready, emailVerified]);

  return (
    <ViewContext.Provider value={c}>
      <AppLayout emailVerified={emailVerified}>
        {!c.auth.ready ? (
          <div className="empty" role="status">
            계정을 확인하고 있어요.
          </div>
        ) : emailVerified ? (
          <EmailVerifiedScreen
            onReturn={() => {
              setEmailVerified(false);
              c.showDialog('accountDialog', { signup: true });
            }}
          />
        ) : target === c.route ? (
          <Page c={c} />
        ) : null}
      </AppLayout>
    </ViewContext.Provider>
  );
}
