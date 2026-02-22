# --- 5. MATH ENGINE (CRASH-PROOF) ---
new_loan_amount = round(arv * refi_ltv, -3)
net_proceeds = round(new_loan_amount - refi_closing, -3)
cash_left = round(total_invested - net_proceeds, -3)

# Safety check for 0% interest rate to avoid ZeroDivisionError
r_monthly = (refi_rate / 100) / 12
n_months = 360

if r_monthly > 0:
    monthly_piti = (new_loan_amount * r_monthly) / (1 - (1 + r_monthly)**-n_months)
else:
    # If interest is 0, it's just Principal / Months
    monthly_piti = new_loan_amount / n_months if n_months > 0 else 0

opex_buffer = monthly_rent * 0.25 
monthly_net = round(monthly_rent - monthly_piti - opex_buffer, 0)

# Safety check for DSCR (cannot divide by 0 mortgage payment)
noi_annual = (monthly_rent - opex_buffer) * 12
debt_annual = monthly_piti * 12

if debt_annual > 0:
    dscr = noi_annual / debt_annual
else:
    # If no debt, DSCR is technically infinite, but we'll set a high floor for the UI
    dscr = 99.0 if noi_annual > 0 else 0.0

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
