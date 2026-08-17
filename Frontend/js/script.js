const API_BASE_URL = "http://localhost:8000";
const state = {
  income: 25000,
  expenses: 18500,
  score: 72,
  transactions: [
    {date:"2026-08-15", type:"expense", title:"Hostel", category:"Housing", amount:7000},
    {date:"2026-08-14", type:"expense", title:"Food", category:"Food", amount:4200},
    {date:"2026-08-01", type:"income", title:"Stipend", category:"Income", amount:25000}
  ],
  consents: [true,true,true,true,true]
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

function showToast(text){
  const t=$("#toast"); t.textContent=text; t.classList.add("show");
  clearTimeout(window.toastTimer); window.toastTimer=setTimeout(()=>t.classList.remove("show"),2200);
}

function showView(id){
  $$(".view").forEach(v=>v.classList.toggle("hidden", v.id!==id));
  $$(".desktop-nav button,.mobile-nav button").forEach(b=>b.classList.toggle("active", b.dataset.view===id));
  window.scrollTo({top:0,behavior:"smooth"});
}

document.addEventListener("click",(e)=>{
  const btn=e.target.closest("[data-view]");
  if(btn){ showView(btn.dataset.view); }
});

function updateDashboard(){
  const cashflow=state.income-state.expenses;
  const rate=state.income ? (cashflow/state.income)*100 : 0;
  $("#incomeValue").textContent=`₹${state.income.toLocaleString("en-IN")}`;
  $("#expenseValue").textContent=`₹${state.expenses.toLocaleString("en-IN")}`;
  $("#cashflowValue").textContent=`${cashflow>=0?"+":"-"}₹${Math.abs(cashflow).toLocaleString("en-IN")}`;
  $("#savingsValue").textContent=`${rate.toFixed(1)}%`;
  $("#scoreValue").textContent=state.score;
  const gauge=document.querySelector(".gauge");
  gauge.style.background=`conic-gradient(#0d4734 0 ${state.score}%,#e7ece9 ${state.score}% 100%)`;
}

function renderChart(){
  const values=[[68,53],[76,50],[88,65],[78,55],[83,60],[95,70]];
  $("#cashflowChart").innerHTML=values.map((v,i)=>`
    <div class="bar-group" title="Month ${i+1}">
      <div class="bar income-bar" style="height:${v[0]}%"></div>
      <div class="bar expense-bar" style="height:${v[1]}%"></div>
    </div>`).join("");
}

function renderTransactions(){
  $("#transactionBody").innerHTML=state.transactions.map(t=>`
    <tr>
      <td>${t.date}</td>
      <td>${t.type}</td>
      <td>${escapeHtml(t.title)}</td>
      <td>${escapeHtml(t.category)}</td>
      <td>${t.type==="income"?"+":"-"}₹${Number(t.amount).toLocaleString("en-IN")}</td>
    </tr>`).join("");
}

function renderAudit(){
  $("#auditBody").innerHTML=state.consents.map((v,i)=>`
    <tr><td>${new Date().toLocaleTimeString()}</td><td>${["Income","Expenses","Transactions","Savings","Borrowing"][i]}</td><td>${v?"Granted":"Revoked"}</td></tr>
  `).join("");
  const count=state.consents.filter(Boolean).length;
  $("#consentCount").textContent=`${count}/5 Consents Granted`;
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
}

$$("[data-consent]").forEach((input,i)=>{
  input.addEventListener("change",()=>{
    state.consents[i]=input.checked;
    renderAudit();
    showToast(input.checked?"Consent granted":"Consent revoked");
  });
});

$("#revokeAll").addEventListener("click",()=>{
  $$("[data-consent]").forEach(i=>i.checked=false);
  state.consents.fill(false); renderAudit(); showToast("All consents revoked");
});

$("#addTransaction").addEventListener("click",()=>{
  const type=$("#txType").value, title=$("#txTitle").value.trim();
  const amount=Number($("#txAmount").value), category=$("#txCategory").value;
  const date=$("#txDate").value || new Date().toISOString().slice(0,10);
  if(!title || !amount){ showToast("Enter a description and amount"); return; }
  state.transactions.unshift({date,type,title,category,amount});
  if(type==="income") state.income+=amount; else state.expenses+=amount;
  $("#txTitle").value=""; $("#txAmount").value="";
  renderTransactions(); updateDashboard();
  showToast("Transaction added");
});

$$(".factor").forEach(btn=>btn.addEventListener("click",()=>{
  const name=btn.dataset.factor;
  const messages={
    "Income Stability":"Your recent income is relatively consistent. More consistent inflows generally support a stronger readiness profile.",
    "Savings Capacity":"Your monthly surplus is positive, indicating room to build savings without assuming additional borrowing.",
    "Expense Volatility":"Your expenses vary across months. Reducing large discretionary swings can improve financial resilience."
  };
  showToast(messages[name]||"Factor details unavailable");
}));

function addMessage(text,type){
  const el=document.createElement("div"); el.className=`message ${type}`; el.textContent=text;
  $("#chat").appendChild(el); $("#chat").scrollTop=$("#chat").scrollHeight;
}

function answerQuestion(q){
  const x=q.toLowerCase();
  let answer;
  if(x.includes("score")) answer=`Your current Credit Readiness Score is ${state.score}/100. The main positive factors are income stability and savings capacity, while expense variation is reducing the score. This is an educational indicator, not an official credit score.`;
  else if(x.includes("spending")) answer=`Your largest current expense is Housing at about ₹7,000, followed by Food at about ₹4,200.`;
  else if(x.includes("save")) answer=`Your current estimated monthly surplus is ₹${(state.income-state.expenses).toLocaleString("en-IN")}. A realistic starting point would be to reserve a portion of that surplus rather than committing all of it.`;
  else answer=`Based on the consented demo data, your income is ₹${state.income.toLocaleString("en-IN")} and expenses are ₹${state.expenses.toLocaleString("en-IN")}. Your estimated monthly surplus is ₹${(state.income-state.expenses).toLocaleString("en-IN")}.`;
  setTimeout(()=>addMessage(answer,"ai"),350);
}

$("#chatForm").addEventListener("submit",(e)=>{
  e.preventDefault();
  const q=$("#chatInput").value.trim(); if(!q)return;
  addMessage(q,"user"); $("#chatInput").value=""; answerQuestion(q);
});

$$(".suggestions button").forEach(b=>b.addEventListener("click",()=>{
  addMessage(b.dataset.question,"user"); answerQuestion(b.dataset.question);
}));

$("#txDate").value=new Date().toISOString().slice(0,10);
renderTransactions(); renderAudit(); renderChart(); updateDashboard();
