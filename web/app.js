const info = document.querySelector('#graph-info');
document.querySelectorAll('.graph button').forEach((node) => node.addEventListener('click', () => {
  document.querySelectorAll('.graph button').forEach((item) => item.removeAttribute('aria-current'));
  node.setAttribute('aria-current', 'true'); info.textContent = node.dataset.info;
}));
document.querySelector('#run').addEventListener('click', async () => {
  const terminal = document.querySelector('#terminal'); terminal.innerHTML = '<span>$ repoimmune replay astropy-12907</span><span>isolating local capsule…</span>';
  await new Promise((resolve) => setTimeout(resolve, 450));
  terminal.innerHTML += '<span style="color:#ff8b8b">✓ buggy.py — expected failure reproduced (exit 1)</span>';
  await new Promise((resolve) => setTimeout(resolve, 350));
  terminal.innerHTML += '<span style="color:#58f2ac">✓ fixed.py — expected behavior passes (exit 0)</span><span>capsule result: VERIFIED</span>';
});

