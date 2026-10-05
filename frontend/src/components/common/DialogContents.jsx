import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../../components/common/Elements.jsx';
export function restartDialog(ctx) {
  return ctx.openDialog('설문을 처음부터 다시 시작할까요?', <div className={"dialog-body reset-summary"}><p>{"첫 7문항부터 새로운 추천을 받을 수 있어요."}</p><div className={"reset-scope"}><strong>{"초기화되는 내용"}</strong><p>{"7·28·30문항의 완료한 답변과 진행 중인 답변, 추천 조건"}</p></div><div className={"reset-retained"}><>{ctx.icon('BookmarkCheck')}{"프로필·찜한 게임·작성한 평가는 유지됩니다."}</></div></div>, <>{ctx.btn('취소', 'close', 'btn ghost')}{ctx.btn('설문 초기화하고 시작', 'confirm-restart', 'btn danger')}</>);
}
export function filtersDialog(ctx) {
  const p = ctx.report().prefs;
  return ctx.openDialog('추천 조건', <Form id={"filter-form"} className={"dialog-body"}><p className={"note"}>{"설문에서 선택한 조건입니다. 바꾸면 추천 게임과 내 취향 랭킹에 함께 반영됩니다."}</p><span className={"field-title"}>{"사용할 기기"}</span><div className={"check-grid"}>{React.Children.toArray(Object.entries(ctx.E.PLATFORM_LABELS).map(([k, v], itemIndex) => <label className={"check"} key={itemIndex}><Field type={"checkbox"} name={"platforms"} value={k} {...ctx.attrs(p.platforms.includes(k) ? 'checked' : '')} />{v}</label>))}</div><span className={"field-title"}>{"추천에서 제외할 요소"}</span><div className={"check-grid"}>{React.Children.toArray(Object.entries(ctx.E.RISK_LABELS).map(([k, v], itemIndex) => <label className={"check"} key={itemIndex}><Field type={"checkbox"} name={"avoid"} value={k} {...ctx.attrs(p.avoid.includes(k) ? 'checked' : '')} />{v}</label>))}</div><p className={"muted"}>{"기기를 선택하지 않으면 모든 기기의 게임을 살펴봅니다."}</p></Form>, <>{ctx.btn('설문 결과로 되돌리기', 'reset-filters', 'btn ghost')}{ctx.btn('조건 적용', 'apply-filters', 'btn primary')}</>);
}
export function customizeBody(ctx) {
  const d = ctx.dialogDraft;
  return ctx.openDialog('게임 포인트 색상', <div className={"dialog-body"}><p className={"note"}>{"사이트의 기본 컬러는 유지하고, 추천 번호와 강조 문구에만 게임 색상을 적용합니다."}</p><span className={"field-title"}>{"색상 기준"}</span><div className={"choice-row"}>{React.Children.toArray([['follow', '추천 게임 따라가기'], ['fixed', '내가 고른 게임'], ['brand', '브랜드 색상']].map(([k, v], itemIndex) => ctx.btn(v, 'home-style', 'tab', `aria-selected="${d.style === k}" data-value="${k}"`)))}</div>{d.style === 'fixed' ? <><span className={"field-title"}>{"색상을 가져올 게임"}</span><div className={"theme-grid"}>{React.Children.toArray(ctx.CATALOG.map((g, itemIndex) => ctx.btn(<><GameImage src={ctx.gameImage(g.id)} alt={""} /><span>{ctx.esc(g.title)}</span></>, 'home-game', 'theme-choice', `data-id="${g.id}" aria-pressed="${d.game === g.id}"`)))}</div></> : ''}</div>, <>{ctx.btn('취소', 'close', 'btn ghost')}{ctx.btn('홈에 적용', 'save-home', 'btn primary')}</>);
}
export function profileEditorBody(ctx) {
  const p = ctx.dialogDraft;
  return ctx.openDialog('프로필 꾸미기', <Form id={"profile-form"} className={"dialog-body"}><label className={"field"}><span>{"닉네임"}</span><Field name={"name"} value={ctx.esc(p.name)} maxLength={"24"} required={true} autoComplete={"nickname"} /></label><label className={"field"}><span>{"한 줄 소개"}</span><Field name={"bio"} value={ctx.esc(p.bio)} maxLength={"90"} /></label><span className={"field-title"}>{"나를 표현할 아이콘"}</span><div className={"choice-row"}>{React.Children.toArray(ctx.avatars.map((a, itemIndex) => ctx.btn(ctx.icon(a), 'avatar', 'avatar-choice', `data-value="${a}" aria-label="${{
        Rocket: '로켓',
        Gamepad2: '게임패드',
        Orbit: '궤도',
        Sparkles: '반짝임',
        ScanFace: '얼굴',
        Trophy: '트로피'
      }[a]}" aria-pressed="${p.avatar === a}"`)))}</div><span className={"field-title"}>{"포인트 컬러"}</span><div className={"choice-row"}>{React.Children.toArray(['#5278ee', '#0ca9c7', '#8857df', '#cd608c'].map((c, i) => ctx.btn('', 'profile-color', 'color-choice', `data-value="${c}" style="--swatch:${c}" aria-label="${['블루', '시안', '퍼플', '핑크'][i]}" aria-pressed="${p.color === c}"`)))}</div><span className={"field-title"}>{"프로필 배경"}</span><div className={"theme-grid"}><>{ctx.btn(<><span style={ctx.style("height:80px;background:linear-gradient(130deg,#00b5e8,#8652ed)")} /><span>{"RecomEngine"}</span></>, 'profile-banner', 'theme-choice', `data-id="brand" aria-pressed="${p.banner === 'brand'}"`)}{React.Children.toArray(['elden', 'cyber', 'stardew', 'baldur', 'unpacking'].map((id, itemIndex) => ctx.btn(<><GameImage src={ctx.gameImage(id)} alt={""} /><span>{ctx.esc(ctx.game(id).title)}</span></>, 'profile-banner', 'theme-choice', `data-id="${id}" aria-pressed="${p.banner === id}"`)))}</></div></Form>, <>{ctx.btn('취소', 'close', 'btn ghost')}{ctx.btn('프로필 저장', 'save-profile', 'btn primary')}</>);
}
export function reviewForm(ctx) {
  const id = ctx.gameRoute()?.id || ctx.reviewGame,
    g = ctx.game(id);
  if (!g) return;
  return ctx.openDialog('내 플레이 경험 남기기', <Form className={"dialog-body"} id={"review-form"}><Field type={"hidden"} name={"game"} value={g.id} /><div className={"review-game-title"}><GameImage src={ctx.gameImage(g.id)} alt={""} /><strong>{ctx.esc(g.title)}</strong></div><label className={"field"}><span>{"내 평점"}</span><Select name={"rating"}>{React.Children.toArray([5, 4, 3, 2, 1].map((v, itemIndex) => <option value={v} key={itemIndex}><>{v}{"점 "}{'★'.repeat(v)}</></option>))}</Select></label><label className={"field"}><span>{"어떤 점이 좋았나요?"}</span><FieldArea name={"text"} maxLength={"1200"} minLength={"10"} required={true} placeholder={"플레이 경험을 10자 이상 남겨주세요."} /></label><p className={"muted"}><>{ctx.esc(ctx.state.profile.name)}{" 이름으로 이 브라우저에만 저장됩니다."}</></p><p className={"form-error"} id={"review-error"} role={"alert"} /></Form>, <>{ctx.btn('취소', 'close', 'btn ghost')}{ctx.btn('내 평가 저장', 'save-review', 'btn primary')}</>);
}
export function answersDialog(ctx, kind) {
  const s = ctx.state[kind];
  if (!s?.completed) return;
  const qs = kind === 'deep' ? s.questions : kind === 'quick' ? s.questions || ctx.E.quickQuestions(ctx.state.track) : s.questions || ctx.E.profileQuestions(s.track || ctx.state.track);
  return ctx.openDialog(ctx.surveyName(kind) + ' · 내 답변', <div className={"dialog-body stack"}>{React.Children.toArray(qs.map((q, i) => <section key={i}><h3 style={ctx.style("font-size:18px;line-height:1.5")}><>{i + 1}{". "}{ctx.esc(q.title)}</></h3><p style={ctx.style("margin-top:9px")}>{q.options.filter(o => s.answers[q.id]?.includes(o.id)).map((o, itemIndex) => ctx.esc(o.label)).join(' · ')}</p></section>))}</div>);
}
export function retake(ctx, kind) {
  return ctx.openDialog('다시 답하기', <div className={"dialog-body"}><p><>{"새 설문이 끝나면 분석 결과를 다시 계산합니다. 진행 중에는 기존 완료 결과가 유지됩니다."}{ctx.draft(kind) ? ' 저장된 미완료 답변은 새로 시작합니다.' : ''}</></p></div>, <>{ctx.btn('취소', 'close', 'btn ghost')}{ctx.btn('새 설문 시작', 'confirm-retake', 'btn primary', `data-kind="${kind}"`)}</>);
}
export function feedbackDialog(ctx, id) {
  const g = ctx.game(id);
  if (!g) return;
  const f = ctx.state.feedback?.[id] || {};
  return ctx.openDialog('이 게임은 어떠셨나요?', <div className={"dialog-body"}><h3>{ctx.esc(g.title)}</h3><div className={"feedback-options"}>{React.Children.toArray([['uninterested', '관심 없음', '비슷한 게임을 덜 추천해요.'], ['disliked', '재미없음', '비슷한 특징의 추천 가중치를 낮춰요.'], ['liked', '재밌음', '비슷한 특징의 게임을 더 추천해요.'], ['played', '이미 플레이함', '이 게임은 추천에서 빼고, 유사 게임은 조금 덜 추천해요.'], ['hidden', '이 게임 추천 안 함', '이 게임만 추천에서 제외해요.']].map(([v, label, sub], itemIndex) => ctx.btn(<><strong>{label}</strong><span>{sub}</span></>, 'feedback-choice', 'feedback-option', `data-id="${id}" data-value="${v}" aria-pressed="${v === 'played' || v === 'hidden' ? !!f[v] : f.sentiment === v}"`)))}</div><p className={"note"}>{"선택 즉시 이 브라우저의 추천 엔진에 저장됩니다. 로고를 눌러 홈으로 돌아가면 갱신된 추천을 볼 수 있어요. 외부 AI 모델로 전송하거나 학습시키지는 않습니다."}</p></div>, <>{ctx.btn('피드백 취소', 'feedback-clear', 'btn ghost', `data-id="${id}"`)}{ctx.btn('완료', 'close', 'btn primary')}</>);
}
export function accountDialog(ctx, signup = false) {
  return ctx.openDialog(signup ? '회원가입' : '로그인', <Form id={"account-form"} className={"dialog-body"} data-signup={signup}>{signup ? <label className={"field"}><span>{"닉네임"}</span><Field name={"name"} required={true} maxLength={"24"} autoComplete={"nickname"} /></label> : ''}<label className={"field"}><span>{"이메일"}</span><Field name={"email"} type={"email"} required={true} maxLength={"254"} autoComplete={"username"} /></label><label className={"field"}><span>{"비밀번호"}</span><Field name={"password"} type={"password"} required={true} minLength={"8"} maxLength={"128"} autoComplete={signup ? 'new-password' : 'current-password'} /></label><p className={"note"}><>{ctx.apiReady ? '연결된 계정 서버를 통해 로그인합니다.' : '현재 계정 서버가 연결되지 않았습니다. 게스트로 이용할 수 있으며 답변은 이 브라우저에 저장됩니다.'}{signup ? ' 현재 게스트의 답변과 찜한 게임을 새 계정에 저장합니다.' : ''}</></p><p id={"account-error"} role={"alert"} /></Form>, <>{ctx.btn(signup ? '이미 계정이 있어요' : '회원가입', 'account-' + (signup ? 'login' : 'signup'), 'btn ghost')}{ctx.btn(signup ? '가입하고 시작' : '로그인', 'account-submit', 'btn primary')}</>);
}