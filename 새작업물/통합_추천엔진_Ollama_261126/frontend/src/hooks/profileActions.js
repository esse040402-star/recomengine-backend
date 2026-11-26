import { toggleFeedback } from '../services/feedbackService';
import { verifyMockEmail } from '../services/accountService';
export function profileActions(c) {
    const form = id => c.forms.current[id], valid = id => form(id)?.reportValidity(), data = id => new FormData(form(id)); return {
        'mode': ({ value }) => c.patch({ mode: value }), 'dismiss-banner': () => c.patch({ bannerDismissed: true }),
        'save': ({ id }) => { c.dispatch({ type: 'save-game', id }); c.toast(c.state.saved.includes(id) ? '찜한 게임에서 뺐어요.' : '찜한 게임에 담았어요.'); },
        'game-feedback': ({ id }) => c.showDialog('feedbackDialog', { id }),
        'feedback-choice': ({ id, value }) => { c.dispatch({ type: 'feedback', id, feedback: toggleFeedback(c.state.feedback[id], value) }); c.toast('취향 피드백을 추천에 반영했어요.'); },
        'feedback-clear': ({ id }) => { const feedback = { ...c.state.feedback }; delete feedback[id]; c.patch({ feedback }); c.closeDialog(); },
        'filters': () => c.showDialog('filtersDialog'),
        'apply-filters': () => { const f = data('filter-form'); c.patch({ filters: { platforms: f.getAll('platforms'), avoid: f.getAll('avoid') } }); c.closeDialog(); },
        'reset-filters': () => { c.patch({ filters: {} }); c.closeDialog(); },
        'customize': () => c.showDialog('customizeBody', {}, c.state.home),
        'home-style': ({ value }) => c.setUI({ dialogDraft: { ...c.dialogDraft, style: value } }),
        'home-game': ({ id }) => c.setUI({ dialogDraft: { ...c.dialogDraft, game: id } }),
        'save-home': () => { c.patch({ home: c.dialogDraft }); c.closeDialog(); c.toast('홈 색상을 적용했어요.'); },
        'apply-theme': ({ id }) => { c.patch({ home: { style: 'fixed', game: id } }); c.goto('home'); c.toast('이 게임의 색상을 홈에 적용했어요.'); },
        'edit-profile': () => c.showDialog('profileEditorBody', {}, c.state.profile),
        'avatar': ({ value }) => c.setUI({ dialogDraft: { ...c.dialogDraft, avatar: value } }),
        'profile-color': ({ value }) => c.setUI({ dialogDraft: { ...c.dialogDraft, color: value } }),
        'profile-banner': ({ id }) => c.setUI({ dialogDraft: { ...c.dialogDraft, banner: id } }),
        'save-profile': () => { if (!valid('profile-form')) return; const f = data('profile-form'), name = String(f.get('name')).trim(); if (!name) return; c.patch({ profile: { ...c.dialogDraft, name, bio: String(f.get('bio')).trim() } }); c.closeDialog(); c.toast('프로필을 저장했어요.'); },
        'write-review': ({ id }) => { c.setUI({ reviewGame: id }); c.showDialog('reviewForm', { id }); },
        'save-review': () => { if (!valid('review-form')) return; const f = data('review-form'), text = String(f.get('text')).trim(); if (text.length < 10) return c.toast('플레이 경험을 10자 이상 입력해주세요.'); const id = f.get('game'); c.patch({ reviews: [{ id: crypto.randomUUID(), game: id, rating: Number(f.get('rating')), createdAt: new Date().toISOString(), text, name: c.state.profile.name }, ...c.state.reviews] }); c.goto('game/' + id + '/reviews'); c.toast('내 평가를 저장했어요.'); },
        'restart-onboarding': () => c.showDialog('restartDialog'),
        'account-login': () => c.showDialog('accountDialog', { signup: false }),
        'account-signup': () => c.showDialog('accountDialog', { signup: true }),

        'account-submit': async () => {
            if (!valid('account-form')) return;

            const formData = Object.fromEntries(data('account-form'));
            const isSignup = c.dialog.params.signup;

            if (isSignup && formData.password !== formData.passwordConfirm) {
                c.toast('비밀번호가 일치하지 않습니다.');
                return;
            }

            try {
                // 인증 후에도 닉네임과 이메일을 다시 채울 수 있도록 저장
                // 비밀번호는 보안상 저장하지 않음
                if (isSignup) {
                    localStorage.setItem(
                        'recomengine-signup-prefill',
                        JSON.stringify({
                            name: formData.name,
                            email: formData.email
                        })
                    );
                }

                const result = await c.authenticate(isSignup, formData);

                if (result?.emailConfirmationRequired) {
                    c.closeDialog();
                    c.showDialog(
                        result.mockVerificationToken ? 'mockEmailVerificationDialog' : 'emailConfirmationDialog',
                        { email: formData.email, token: result.mockVerificationToken }
                    );
                    c.toast(result.mockVerificationToken
                        ? '시연용 이메일 인증 대기 상태입니다.'
                        : '인증 메일을 보냈어요. 이메일을 확인해 주세요.');
                    return;
                }

                if (result?.ok || result === true) {
                    if (isSignup) {
                        // 회원가입 완료 후에는 게스트와 동일한 이용 경험 선택 화면으로 이동
                        c.setUI({ forceOnboarding: true });
                        c.goto('track-select');
                        c.toast(result.guestSessionClaimFailed
                            ? '회원가입은 완료됐지만 이전 비회원 진단 연결에 실패했어요. 다시 로그인해 연결을 재시도할 수 있어요.'
                            : '회원가입이 완료되었습니다. 게임 이용 경험을 선택해 주세요.');
                    } else {
                        // 로그인은 기존처럼 메인 화면으로 이동
                        c.setUI({ forceOnboarding: false });
                        c.goto('home');
                        c.toast(result.guestSessionClaimFailed
                            ? '로그인되었습니다. 다만 이전 비회원 진단 연결에 실패했어요. 잠시 후 다시 시도해 주세요.'
                            : '로그인되었습니다.');
                    }
                }
            } catch (e) {
                c.toast(e.message);
            }
        },

        'mock-email-verify': async () => {
            const { token, email } = c.dialog?.params || {};
            try {
                await verifyMockEmail(token);
                c.showDialog('mockEmailVerifiedDialog', { email });
            } catch (error) {
                c.toast(error.message || '시연용 이메일 인증에 실패했어요.');
            }
        },
        'mock-email-open-login': () => {
            const { email } = c.dialog?.params || {};
            try {
                localStorage.setItem('recomengine-signup-prefill', JSON.stringify({ email }));
            } catch { }
            c.showDialog('accountDialog', { signup: false });
        },
        'account-recover-local': () => { c.recoverLocal(); c.toast('이 기기의 미전송 변경을 복구했어요.'); },
        'account-retry-save': async () => { try { await c.retrySave(); } catch (e) { c.toast(e.message) } },
        'account-logout': async () => { try { if (await c.logout()) { c.setUI({ forceOnboarding: true, guidedChat: null, chatTurns: [], chatBusy: false }); c.goto('welcome'); } } catch (e) { c.toast(e.message) } }
    };
}
