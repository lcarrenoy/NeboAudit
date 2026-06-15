content = """import React, { useState, useEffect, useCallback } from 'react';
import { Shield, AlertTriangle, CheckCircle, Lock, RefreshCw, Building2 } from 'lucide-react';

const TENANTS = [
  { id: 1, code: 'FNB', name: 'First National Bank' },
  { id: 2, code: 'MMC', name: 'Mega Mortgage Corp' },
];

const ACTION_COLORS = {
  AUTO_BLOCK:    { bg: '#FEE2E2', color: '#991B1B', icon: 'lock' },
  SENIOR_REVIEW: { bg: '#FEF3C7', color: '#92400E', icon: 'alert' },
  FAST_TRACK:    { bg: '#D1FAE5', color: '#065F46', icon: 'check' },
};

function ActionBadge({ action }) {
  const style = ACTION_COLORS[action] || { bg: '#F3F4F6', color: '#374151', icon: 'check' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
      backgroundColor: style.bg, color: style.color,
    }}>
      {action === 'AUTO_BLOCK'    && <Lock size={12} />}
      {action === 'SENIOR_REVIEW' && <AlertTriangle size={12} />}
      {action === 'FAST_TRACK'    && <CheckCircle size={12} />}
      {action}
    </span>
  );
}

export default function App() {
  const [loans, setLoans]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [tenantId, setTenantId] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const [page, setPage]         = useState(1);
  const PAGE_SIZE = 10;

  const fetchData = useCallback(async (tid, pg) => {
    setLoading(true);
    setError('');
    try {
      const authRes = await fetch('http://localhost:5267/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario: 'admin', password: 'admin123', tenantId: tid }),
      });
      const { token } = await authRes.json();
      const loansRes = await fetch(
        `http://localhost:5267/api/loans?page=${pg}&pageSize=${PAGE_SIZE}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const result = await loansRes.json();
      setLoans(result.data || []);
      setTotalRows(result.totalRows || 0);
    } catch (e) {
      setError('No se pudo conectar con la API .NET 9 (puerto 5267).');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { setPage(1); fetchData(tenantId, 1); }, [tenantId, fetchData]);
  useEffect(() => { fetchData(tenantId, page); }, [page, tenantId, fetchData]);

  const tenant     = TENANTS.find(t => t.id === tenantId);
  const totalPages = Math.ceil(totalRows / PAGE_SIZE);
  const blocked    = loans.filter(l => l.automatedAction === 'AUTO_BLOCK').length;
  const review     = loans.filter(l => l.automatedAction === 'SENIOR_REVIEW').length;

  return (
    <div style={{ fontFamily: 'Segoe UI, sans-serif', background: '#F3F4F6', minHeight: '100vh', padding: 24 }}>

      {/* Header */}
      <header style={{
        background: '#1F4E78', color: '#fff', padding: '18px 24px',
        borderRadius: 10, marginBottom: 24,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Shield size={28} />
          <div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>NeboAudit Platform</div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Mortgage Compliance Intelligence</div>
          </div>
        </div>

        {/* Tenant selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Building2 size={16} style={{ opacity: 0.8 }} />
          <select
            value={tenantId}
            onChange={e => setTenantId(Number(e.target.value))}
            style={{
              background: 'rgba(255,255,255,0.15)', color: '#fff',
              border: '1px solid rgba(255,255,255,0.3)', borderRadius: 6,
              padding: '6px 12px', fontSize: 13, cursor: 'pointer',
            }}
          >
            {TENANTS.map(t => (
              <option key={t.id} value={t.id} style={{ background: '#1F4E78' }}>
                {t.code} — {t.name}
              </option>
            ))}
          </select>
          <span style={{
            background: '#2E7D32', fontSize: 11, fontWeight: 700,
            padding: '4px 10px', borderRadius: 20,
          }}>LIVE</span>
        </div>
      </header>

      {error && (
        <div style={{ background: '#FEE2E2', color: '#991B1B', padding: 14, borderRadius: 8, marginBottom: 20, fontWeight: 600 }}>
          {error}
        </div>
      )}

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Banco activo',      value: tenant?.code,  sub: tenant?.name,        color: '#185FA5' },
          { label: 'Creditos (pagina)', value: loans.length,  sub: `${totalRows} total`, color: '#1D9E75' },
          { label: 'AUTO_BLOCK',        value: blocked,       sub: 'en esta pagina',     color: '#A32D2D' },
          { label: 'SENIOR_REVIEW',     value: review,        sub: 'en esta pagina',     color: '#EF9F27' },
        ].map(k => (
          <div key={k.label} style={{
            background: '#fff', borderRadius: 10, padding: '16px 20px',
            borderTop: `4px solid ${k.color}`, boxShadow: '0 1px 4px rgba(0,0,0,.06)',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>{k.label}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: k.color, margin: '6px 0 2px' }}>{k.value}</div>
            <div style={{ fontSize: 11, color: '#9CA3AF' }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,.06)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1F2937' }}>
            Portfolio — {tenant?.name}
          </div>
          <button
            onClick={() => fetchData(tenantId, page)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#F3F4F6', border: 'none', padding: '7px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#9CA3AF' }}>Cargando datos...</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead style={{ background: '#F9FAFB' }}>
              <tr>
                {['ID Credito','Tipo','Monto','LTV','DTI','Risk Score','Accion IA'].map(h => (
                  <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#6B7280', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', borderBottom: '2px solid #E5E7EB' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loans.map(loan => (
                <tr key={loan.loanId} style={{ borderBottom: '1px solid #F3F4F6' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: '#185FA5' }}>{loan.externalLoanId}</td>
                  <td style={{ padding: '10px 14px' }}>{loan.loanType}</td>
                  <td style={{ padding: '10px 14px' }}>${Number(loan.loanAmount).toLocaleString()}</td>
                  <td style={{ padding: '10px 14px' }}>{loan.ltv}%</td>
                  <td style={{ padding: '10px 14px' }}>{loan.dti}%</td>
                  <td style={{ padding: '10px 14px', fontWeight: 600 }}>{Number(loan.riskScore).toFixed(4)}</td>
                  <td style={{ padding: '10px 14px' }}><ActionBadge action={loan.automatedAction} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13, color: '#6B7280' }}>
          <span>Pagina {page} de {totalPages} ({totalRows} registros)</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}
              style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #E5E7EB', background: page===1?'#F9FAFB':'#fff', cursor: page===1?'default':'pointer' }}>
              Anterior
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page === totalPages}
              style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #E5E7EB', background: page===totalPages?'#F9FAFB':'#fff', cursor: page===totalPages?'default':'pointer' }}>
              Siguiente
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
"""

with open(r"C:\Dev\NeboAudit Platform\neboaudit-frontend\src\App.js", "w", encoding="utf-8") as f:
    f.write(content)

print("App.js actualizado correctamente")
