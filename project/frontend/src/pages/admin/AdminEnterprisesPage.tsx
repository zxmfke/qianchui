import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Building2,
  Search,
  Plus,
  Edit2,
  Trash2,
  Users,
  BookOpen,
  MessageSquare,
  Loader2,
  X,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { adminService, type AdminEnterprise } from '@/services/admin';

interface FormData {
  name: string;
  industry: string;
  is_active: boolean;
}

const EMPTY_FORM: FormData = { name: '', industry: '', is_active: true };

export default function AdminEnterprisesPage() {
  const { t } = useTranslation();
  const [enterprises, setEnterprises] = useState<AdminEnterprise[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const PAGE_SIZE = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminService.listEnterprises({ page, page_size: PAGE_SIZE, search });
      setEnterprises(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  };

  const openEdit = (ent: AdminEnterprise) => {
    setEditId(ent.id);
    setForm({ name: ent.name, industry: ent.industry || '', is_active: ent.is_active });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        await adminService.updateEnterprise(editId, {
          name: form.name, industry: form.industry || undefined, is_active: form.is_active,
        });
      } else {
        await adminService.createEnterprise({
          name: form.name, industry: form.industry || undefined, is_active: form.is_active,
        });
      }
      setShowModal(false);
      load();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(t('admin.enterprises.confirmDelete', { name }))) return;
    try {
      await adminService.deleteEnterprise(id);
      load();
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
          <h1 className="text-xl font-bold text-slate-100">{t('admin.enterprises.title')}</h1>
          <p className="text-sm text-slate-400 mt-1">
            {t('admin.enterprises.subtitle', { count: total })}
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-500 text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('admin.enterprises.create')}
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder={t('admin.enterprises.searchPlaceholder')}
          className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        />
      </div>

      {/* Table */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.enterprises.name')}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.enterprises.industry')}
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.enterprises.status')}
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <Users className="w-3.5 h-3.5 inline" />
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <BookOpen className="w-3.5 h-3.5 inline" />
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <MessageSquare className="w-3.5 h-3.5 inline" />
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.enterprises.createdAt')}
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {t('admin.enterprises.actions')}
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
              ) : enterprises.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500">
                    {t('common.noData')}
                  </td>
                </tr>
              ) : (
                enterprises.map((ent) => (
                  <tr key={ent.id} className="border-b border-slate-700/30 hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span className="text-slate-200 font-medium">{ent.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{ent.industry || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      {ent.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-emerald-500/10 text-emerald-400">
                          <CheckCircle2 className="w-3 h-3" />
                          {t('admin.enterprises.active')}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/10 text-red-400">
                          <XCircle className="w-3 h-3" />
                          {t('admin.enterprises.inactive')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center text-slate-300 tabular-nums">{ent.user_count}</td>
                    <td className="px-4 py-3 text-center text-slate-300 tabular-nums">{ent.script_count}</td>
                    <td className="px-4 py-3 text-center text-slate-300 tabular-nums">{ent.conversation_count}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(ent.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(ent)}
                          className="p-1.5 rounded-md text-slate-400 hover:text-amber-400 hover:bg-slate-700/50 transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(ent.id, ent.name)}
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
          <div className="w-full max-w-[440px] mx-4 bg-slate-800 border border-slate-600 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700">
              <h3 className="text-sm font-semibold text-slate-200">
                {editId ? t('admin.enterprises.edit') : t('admin.enterprises.create')}
              </h3>
              <button onClick={() => setShowModal(false)} className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">{t('admin.enterprises.name')}</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">{t('admin.enterprises.industry')}</label>
                <input
                  value={form.industry}
                  onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500/50"
                />
                <label className="text-sm text-slate-300">{t('admin.enterprises.isActive')}</label>
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
                disabled={saving || !form.name.trim()}
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
