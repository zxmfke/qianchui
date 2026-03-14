import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Users,
  Search,
  Plus,
  Edit2,
  Trash2,
  Loader2,
  X,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Building2,
  Shield,
  User as UserIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { adminService, type AdminUser, type AdminEnterprise } from '@/services/admin';

interface FormData {
  email: string;
  username: string;
  password: string;
  role: string;
  enterprise_id: string;
  is_active: boolean;
}

const EMPTY_FORM: FormData = {
  email: '', username: '', password: '', role: 'staff', enterprise_id: '', is_active: true,
};

const ROLES = ['super_admin', 'admin', 'manager', 'staff'] as const;

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    super_admin: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    admin: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
    manager: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    staff: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border', colors[role] || colors.staff)}>
      {role === 'super_admin' && <Shield className="w-2.5 h-2.5" />}
      {role}
    </span>
  );
}

export default function AdminAccountsPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [enterprises, setEnterprises] = useState<AdminEnterprise[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [filterEnterprise, setFilterEnterprise] = useState('');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const PAGE_SIZE = 15;

  const loadEnterprises = useCallback(async () => {
    try {
      const res = await adminService.listEnterprises({ page_size: 100 });
      setEnterprises(res.items);
    } catch (e) {
      console.error(e);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: PAGE_SIZE, search };
      if (filterRole) params.role = filterRole;
      if (filterEnterprise) params.enterprise_id = filterEnterprise;
      const res = await adminService.listUsers(params as any);
      setUsers(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterRole, filterEnterprise]);

  useEffect(() => { loadEnterprises(); }, [loadEnterprises]);
  useEffect(() => { loadUsers(); }, [loadUsers]);

  const openCreate = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  };

  const openEdit = (u: AdminUser) => {
    setEditId(u.id);
    setForm({
      email: u.email, username: u.username, password: '', role: u.role,
      enterprise_id: u.enterprise_id, is_active: u.is_active,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.username.trim() || !form.enterprise_id) return;
    setSaving(true);
    try {
      if (editId) {
        const data: Record<string, unknown> = {
          email: form.email, username: form.username, role: form.role,
          is_active: form.is_active, enterprise_id: form.enterprise_id,
        };
        if (form.password) data.password = form.password;
        await adminService.updateUser(editId, data as any);
      } else {
        await adminService.createUser({
          email: form.email, username: form.username, password: form.password,
          role: form.role, enterprise_id: form.enterprise_id, is_active: form.is_active,
        });
      }
      setShowModal(false);
      loadUsers();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(t('admin.accounts.confirmDelete', { name }))) return;
    try {
      await adminService.deleteUser(id);
      loadUsers();
    } catch (e) {
      console.error(e);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-5 max-w-[1400px] w-full pt-14 lg:pt-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">{t('admin.accounts.title')}</h1>
          <p className="text-sm text-slate-400 mt-1">
            {t('admin.accounts.subtitle', { count: total })}
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-500 text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('admin.accounts.create')}
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder={t('admin.accounts.searchPlaceholder')}
            className="bg-slate-800/60 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50 w-60"
          />
        </div>
        <select
          value={filterRole}
          onChange={(e) => { setFilterRole(e.target.value); setPage(1); }}
          className="bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        >
          <option value="">{t('admin.accounts.allRoles')}</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select
          value={filterEnterprise}
          onChange={(e) => { setFilterEnterprise(e.target.value); setPage(1); }}
          className="bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-amber-500/50 max-w-[200px]"
        >
          <option value="">{t('admin.accounts.allEnterprises')}</option>
          {enterprises.map((ent) => (
            <option key={ent.id} value={ent.id}>{ent.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.username')}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.email')}
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.role')}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.enterprise')}
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.status')}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.lastLogin')}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.createdAt')}
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.accounts.actions')}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12">
                    <Loader2 className="w-6 h-6 text-amber-400 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500">
                    {t('common.noData')}
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-b border-slate-700/30 hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-slate-200 font-medium">{u.username}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{u.email}</td>
                    <td className="px-4 py-3 text-center">
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-xs text-slate-300">
                        <Building2 className="w-3 h-3 text-amber-400" />
                        {u.enterprise_name || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.is_active ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 mx-auto" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400 mx-auto" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {u.last_login_at
                        ? new Date(u.last_login_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
                        : <span className="text-slate-600">从未登录</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(u)}
                          className="p-1.5 rounded-md text-slate-400 hover:text-amber-400 hover:bg-slate-700/50 transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(u.id, u.username)}
                          className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-slate-700/50 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
            <span className="text-xs text-slate-500">
              {t('admin.pagination.showing', {
                from: (page - 1) * PAGE_SIZE + 1,
                to: Math.min(page * PAGE_SIZE, total),
                total,
              })}
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 text-xs text-slate-400 tabular-nums">{page} / {totalPages}</span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-[480px] mx-4 bg-slate-800 border border-slate-600 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700">
              <h3 className="text-sm font-semibold text-slate-200">
                {editId ? t('admin.accounts.edit') : t('admin.accounts.create')}
              </h3>
              <button onClick={() => setShowModal(false)} className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">{t('admin.accounts.username')}</label>
                  <input
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">{t('admin.accounts.email')}</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">
                  {t('admin.accounts.password')}
                  {editId && <span className="text-slate-500 ml-1">({t('admin.accounts.leaveEmptyKeep')})</span>}
                </label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">{t('admin.accounts.role')}</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">{t('admin.accounts.enterprise')}</label>
                  <select
                    value={form.enterprise_id}
                    onChange={(e) => setForm((f) => ({ ...f, enterprise_id: e.target.value }))}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  >
                    <option value="">{t('admin.accounts.selectEnterprise')}</option>
                    {enterprises.map((ent) => (
                      <option key={ent.id} value={ent.id}>{ent.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500/50"
                />
                <label className="text-sm text-slate-300">{t('admin.accounts.isActive')}</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 px-5 py-3 border-t border-slate-700">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 bg-slate-700/50 hover:bg-slate-700 transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.username.trim() || !form.enterprise_id || (!editId && !form.password)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-500 text-white transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
