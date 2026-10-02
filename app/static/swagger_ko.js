/* Swagger(/docs) 화면의 영어 고정 문구 옆에 한국어 설명을 붙입니다.
   Swagger UI 자체에는 한국어 설정이 없어서, 화면에 그려진 글자를 찾아 바꿉니다.
   번역을 고치거나 추가하려면 아래 LABELS 만 수정하세요. (예시 JSON·코드·우리가 쓴 설명문은 건드리지 않습니다) */
(function () {
  "use strict";

  var LABELS = {
    "Parameters": "Parameters (입력값)",
    "No parameters": "No parameters (입력값 없음)",
    "Name": "Name (이름)",
    "Description": "Description (설명)",
    "Request body": "Request body (요청 내용)",
    "required": "required (필수)",
    "Default value": "Default value (기본값)",
    "Available values": "Available values (선택 가능한 값)",
    "Send empty value": "Send empty value (빈 값 보내기)",
    "Try it out": "Try it out (직접 실행해 보기)",
    "Execute": "Execute (실행)",
    "Cancel": "Cancel (취소)",
    "Clear": "Clear (결과 지우기)",
    "Responses": "Responses (응답)",
    "Code": "Code (상태 코드)",
    "Details": "Details (상세)",
    "Links": "Links (연결)",
    "No links": "No links (없음)",
    "Media type": "Media type (데이터 형식)",
    "Controls Accept header.": "Controls Accept header. (받을 응답 형식 설정 · 그대로 두세요)",
    "header.": "header. (받을 응답 형식 설정 · 그대로 두세요)",
    "Example Value": "Example Value (예시 값)",
    "Edit Value": "Edit Value (입력 내용 수정)",
    "Schema": "Schema (구조 설명)",
    "Schemas": "Schemas (데이터 구조 목록)",
    "Server response": "Server response (서버 응답)",
    "Response body": "Response body (응답 내용)",
    "Response headers": "Response headers (응답 헤더)",
    "Request duration": "Request duration (걸린 시간)",
    "Request URL": "Request URL (요청 주소)",
    "Curl": "Curl (터미널에서 같은 요청을 보내는 명령어)",
    "Download": "Download (내려받기)",
    "Undocumented": "Undocumented (문서에 없는 응답)",
    "Successful Response": "Successful Response (성공 응답)",
    "Validation Error": "Validation Error (입력값 오류)",
    "Loading...": "Loading... (불러오는 중)",
    "(path)": "(path · 주소 안에 들어가는 값)",
    "(query)": "(query · 주소 뒤 ? 에 붙는 값)",
    "(header)": "(header · 요청 헤더에 넣는 값)",
    "(cookie)": "(cookie · 쿠키 값)"
  };

  // 데이터 종류: "string", "string($uuid)", "array[string]" 처럼 정확히 이 형태일 때만
  var TYPES = { string: "문자열", integer: "정수", number: "숫자", boolean: "참/거짓", array: "목록", object: "객체", "null": "값 없음" };
  var TYPE_RE = /^(string|integer|number|boolean|array|object|null)(\(\$[\w-]+\)|\[[^\]]*\])?$/;

  // 예시 JSON, 입력칸, 우리가 직접 쓴 한국어 설명/제목 영역은 건드리지 않는다
  var SKIP = "pre, code, textarea, input, select, option, .microlight, .markdown, .renderedMarkdown, .info, " +
             ".opblock-summary-path, .opblock-summary-description, .opblock-tag small";

  function translate(text) {
    if (typeof text !== "string") return null;
    var trimmed = text.trim();
    if (!trimmed) return null;
    var out = Object.prototype.hasOwnProperty.call(LABELS, trimmed) ? LABELS[trimmed] : null;
    if (!out) {
      var m = TYPE_RE.exec(trimmed);
      if (m) out = trimmed + " (" + TYPES[m[1]] + ")";
    }
    if (!out) return null;
    var lead = /^\s*/.exec(text)[0];
    var tail = /\s*$/.exec(text)[0];
    return lead + out + tail;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { translate: translate, LABELS: LABELS };  // Node 테스트용
  }
  if (typeof document === "undefined") return;

  function apply(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var node, todo = [];
    while ((node = walker.nextNode())) {
      var parent = node.parentElement;
      if (!parent || parent.closest(SKIP)) continue;
      var next = translate(node.nodeValue);
      if (next !== null && next !== node.nodeValue) todo.push([node, next]);
    }
    for (var i = 0; i < todo.length; i++) todo[i][0].nodeValue = todo[i][1];
  }

  // 화면은 펼치고 실행할 때마다 다시 그려지므로, 바뀔 때마다 한 번씩(프레임당 1회) 다시 적용한다.
  // 이미 바꾼 글자는 translate() 가 null 을 돌려주므로 무한 반복되지 않는다.
  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      var root = document.getElementById("swagger-ui");
      if (root) apply(root);
    });
  }
  new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true, characterData: true });
  schedule();
})();
