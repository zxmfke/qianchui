import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Settings,
  Building2,
  Users,
  Cpu,
  Key,
  Save,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Globe,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import i18n from '@/i18n';
import { resetOnboarding } from '@/components/onboarding/OnboardingProvider';

type SettingsTab = 'enterprise' | 'team' | 'model' | 'apikeys' | 'language';

export default function SettingsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<SettingsTab>('enterprise');
  const [showApiKey, setShowApiKey] = useState(false);

  const settingsTabs: { key: SettingsTab; labelKey: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { key: 'enterprise', labelKey: 'settings.enterprise', icon: Building2 },
    { key: 'team', labelKey: 'settings.team', icon: Users },
    { key: 'model', labelKey: 'settings.model', icon: Cpu },
    { key: 'apikeys', labelKey: 'settings.apikeys', icon: Key },
    { key: 'language', labelKey: 'settings.language', icon: Globe },
  ];

  const handleLanguageChange = (lng: string) => {
    localStorage.setItem('lang', lng);
    i18n.changeLanguage(lng);
  };

  const [enterprise, setEnterprise] = useState({
    name: '',
    industry: 'medical',
    description: '',
  });

  useEffect(() => {
    setEnterprise((prev) => ({
      ...prev,
      name: prev.name || t('settings.defaultEnterpriseName'),
      description: prev.description || t('settings.defaultEnterpriseDesc'),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [modelConfig, setModelConfig] = useState({
    apiKey: 'sk-xxxx****xxxx',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4',
    temperature: 0.7,
    maxTokens: 4096,
  });

  const [apiKeys, setApiKeys] = useState([
    { id: '1', nameKey: 'settings.envProduction', key: 'qc-prod-xxxx****', created_at: '2026-02-01', last_used: '2026-02-28' },
    { id: '2', nameKey: 'settings.envTest', key: 'qc-test-xxxx****', created_at: '2026-02-10', last_used: '2026-02-27' },
  ]);

  const [teamMembers] = useState([
    { id: '1', name: '张明', username: 'zhangming', role: 'admin', status: 'active' },
    { id: '2', name: '李婷', username: 'liting', role: 'manager', status: 'active' },
    { id: '3', name: '王浩', username: 'wanghao', role: 'agent', status: 'active' },
    { id: '4', name: '刘芳', username: 'liufang', role: 'agent', status: 'inactive' },
  ]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Settings className="w-4 h-4 text-indigo-400" />
        <h1 className="text-lg font-bold text-slate-100">{t('settings.title')}</h1>
      </div>

      <div className="flex gap-4">
        {/* Sidebar tabs */}
        <div className="w-40 space-y-1">
          {settingsTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left',
                activeTab === tab.key
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800',
              )}
            >
              <tab.icon className="w-4 h-4" />
              {t(tab.labelKey)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 max-w-2xl">
          {activeTab === 'enterprise' && (
            <div className="glass-card p-4 space-y-4">
              <h2 className="text-xs font-semibold text-slate-200">{t('settings.enterprise')}</h2>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.enterpriseName')}</label>
                <input
                  type="text"
                  value={enterprise.name}
                  onChange={(e) => setEnterprise({ ...enterprise, name: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.industry')}</label>
                <select
                  value={enterprise.industry}
                  onChange={(e) => setEnterprise({ ...enterprise, industry: e.target.value })}
                  className="input-field"
                >
                  <option value="medical">{t('settings.industryOptions.medical')}</option>
                  <option value="cosmeticMedical">{t('settings.industryOptions.cosmeticMedical')}</option>
                  <option value="education">{t('settings.industryOptions.education')}</option>
                  <option value="ecommerce">{t('settings.industryOptions.ecommerce')}</option>
                  <option value="finance">{t('settings.industryOptions.finance')}</option>
                  <option value="other">{t('settings.industryOptions.other')}</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.enterpriseDesc')}</label>
                <textarea
                  value={enterprise.description}
                  onChange={(e) => setEnterprise({ ...enterprise, description: e.target.value })}
                  rows={3}
                  className="input-field resize-none"
                />
              </div>
              <button className="btn-primary flex items-center gap-2">
                <Save className="w-4 h-4" /> {t('common.save')}
              </button>
            </div>
          )}

          {activeTab === 'language' && (
            <div className="glass-card p-4 space-y-4">
              <h2 className="text-sm font-semibold text-slate-200">{t('settings.language')}</h2>
              <div className="flex gap-3">
                <button
                  onClick={() => handleLanguageChange('zh')}
                  className={cn(
                    'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all',
                    i18n.language === 'zh' || i18n.language?.startsWith('zh')
                      ? 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30'
                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600',
                  )}
                >
                  {t('settings.langZh')}
                </button>
                <button
                  onClick={() => handleLanguageChange('en')}
                  className={cn(
                    'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all',
                    i18n.language === 'en'
                      ? 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30'
                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600',
                  )}
                >
                  {t('settings.langEn')}
                </button>
              </div>
              <p className="text-xs text-slate-500">
                {t('settings.langSaved')}
              </p>

              <div className="mt-4 pt-4 border-t border-slate-700">
                <button
                  onClick={() => {
                    resetOnboarding();
                    window.location.reload();
                  }}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-slate-700/50 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {t('onboarding.restartTour')}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'team' && (
            <div className="glass-card p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-slate-200">{t('settings.teamMembers')}</h2>
                <button className="btn-primary text-xs flex items-center gap-2">
                  <Plus className="w-4 h-4" /> {t('settings.inviteMember')}
                </button>
              </div>
              <div className="space-y-1.5">
                {teamMembers.map((member) => (
                  <div key={member.id} className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                      {member.name.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-slate-200">{member.name}</p>
                      <p className="text-xs text-slate-500">@{member.username}</p>
                    </div>
                    <span
                      className={cn(
                        'badge border',
                        member.role === 'admin' && 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
                        member.role === 'manager' && 'bg-amber-500/20 text-amber-400 border-amber-500/30',
                        member.role === 'agent' && 'bg-slate-500/20 text-slate-400 border-slate-500/30',
                      )}
                    >
                      {{ admin: t('settings.roleAdmin'), manager: t('settings.roleManager'), agent: t('settings.roleAgent') }[member.role]}
                    </span>
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full',
                        member.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600',
                      )}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'model' && (
            <div className="glass-card p-4 space-y-4">
              <h2 className="text-xs font-semibold text-slate-200">{t('settings.modelConfig')}</h2>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.apiKey')}</label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={modelConfig.apiKey}
                    onChange={(e) => setModelConfig({ ...modelConfig, apiKey: e.target.value })}
                    className="input-field pr-10"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.baseUrl')}</label>
                <input
                  type="text"
                  value={modelConfig.baseUrl}
                  onChange={(e) => setModelConfig({ ...modelConfig, baseUrl: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('settings.modelLabel')}</label>
                <select
                  value={modelConfig.model}
                  onChange={(e) => setModelConfig({ ...modelConfig, model: e.target.value })}
                  className="input-field"
                >
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="claude-3-opus">Claude 3 Opus</option>
                  <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                  <option value="deepseek-v3">DeepSeek V3</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    {t('settings.temperature')} ({modelConfig.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={modelConfig.temperature}
                    onChange={(e) => setModelConfig({ ...modelConfig, temperature: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">{t('settings.maxTokens')}</label>
                  <input
                    type="number"
                    value={modelConfig.maxTokens}
                    onChange={(e) => setModelConfig({ ...modelConfig, maxTokens: parseInt(e.target.value) })}
                    className="input-field"
                  />
                </div>
              </div>
              <button className="btn-primary flex items-center gap-2">
                <Save className="w-4 h-4" /> {t('settings.saveConfig')}
              </button>
            </div>
          )}

          {activeTab === 'apikeys' && (
            <div className="glass-card p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-slate-200">{t('settings.apiKeyManagement')}</h2>
                <button className="btn-primary text-xs flex items-center gap-2">
                  <Plus className="w-4 h-4" /> {t('settings.createKey')}
                </button>
              </div>
              <div className="space-y-2">
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center gap-2 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                    <Key className="w-4 h-4 text-slate-500 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-xs text-slate-200">{key.name}</p>
                      <p className="text-xs text-slate-500 font-mono">{key.key}</p>
                    </div>
                    <div className="text-right text-xs text-slate-500">
                      <p>{t('settings.createdAt')} {key.created_at}</p>
                      <p>{t('settings.lastUsed')} {key.last_used}</p>
                    </div>
                    <button className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <p className="text-xs text-slate-400">
                  ⚠️ {t('settings.apiKeyWarning')}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
