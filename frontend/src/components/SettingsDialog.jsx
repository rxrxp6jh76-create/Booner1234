import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Zap, Activity, Shield, Cloud, Clock } from 'lucide-react';

const SettingsDialog = ({ open, onOpenChange, settings, onSave }) => {
  const [formData, setFormData] = useState(() => {
    const defaults = {
      trading_mode: 'neutral',
      auto_trading: false,
      autonomous_ki_enabled: true,
      use_ai_analysis: true,
      ai_provider: 'emergent',
      ai_model: 'gpt-5',
      swing_trading_enabled: true,
      day_trading_enabled: true,
      scalping_enabled: false,
      momentum_enabled: true,
      mean_reversion_enabled: true,
      breakout_enabled: true,
      grid_enabled: false,
      swing_stop_loss_percent: 2.5,
      swing_take_profit_percent: 4.0,
      swing_max_positions: 5,
      day_stop_loss_percent: 1.2,
      day_take_profit_percent: 2.0,
      day_max_positions: 10,
      scalping_stop_loss_percent: 0.15,
      scalping_take_profit_percent: 0.25,
      scalping_max_positions: 2,
      momentum_stop_loss_percent: 2.5,
      momentum_take_profit_percent: 5.0,
      momentum_max_positions: 5,
      mean_reversion_stop_loss_percent: 1.5,
      mean_reversion_take_profit_percent: 2.0,
      mean_reversion_max_positions: 4,
      breakout_stop_loss_percent: 2.0,
      breakout_take_profit_percent: 4.0,
      breakout_max_positions: 3,
      grid_stop_loss_percent: 3.0,
      grid_max_positions: 8,
      grid_size_pips: 50,
      grid_levels: 5,
      max_trades_per_hour: 5,
      position_size: 0.1,
      max_portfolio_risk_percent: 20.0,
      use_trailing_stop: true,
      trailing_stop_distance: 1.5,
      auto_close_profitable_daily: true,
      auto_close_all_friday: true,
      auto_close_minutes_before: 10,
      active_platforms: [],
    };

    if (settings) {
      return { ...defaults, ...settings };
    }
    return defaults;
  });

  useEffect(() => {
    if (!open || !settings) return;

    const loadMarketHours = async () => {
      try {
        const API_URL = process.env.REACT_APP_BACKEND_URL || '';
        const response = await fetch(`${API_URL}/api/market/hours/all`);
        if (response.ok) {
          const data = await response.json();
          const marketHours = data.market_hours || {};

          const hoursData = {};
          Object.entries(marketHours).forEach(([asset, config]) => {
            const assetLower = asset.toLowerCase();
            hoursData[`${assetLower}_market_open`] = config.open_time || '22:00';
            hoursData[`${assetLower}_market_close`] = config.close_time || '21:00';
            hoursData[`${assetLower}_allow_weekend`] = config.allow_weekend || config.is_24_7 || false;
          });

          setFormData((prev) => ({ ...prev, ...hoursData }));
          console.log('✅ Handelszeiten geladen:', Object.keys(hoursData).length, 'Einträge');
        }
      } catch (err) {
        console.error('Fehler beim Laden der Handelszeiten:', err);
      }
    };

    loadMarketHours();

    const defaults = {
      id: 'trading_settings',
      auto_trading: false,
      use_ai_analysis: true,
      use_llm_confirmation: false,
      ai_provider: 'emergent',
      ai_model: 'gpt-5',
      stop_loss_percent: 2.0,
      take_profit_percent: 4.0,
      use_trailing_stop: false,
      trailing_stop_distance: 1.5,
      max_trades_per_hour: 10,
      combined_max_balance_percent_per_platform: 20.0,
      rsi_oversold_threshold: 30,
      rsi_overbought_threshold: 70,
      macd_signal_threshold: 0,
      mt5_libertex_account_id: '5cc9abd1-671a-447e-ab93-5abbfe0ed941',
      mt5_icmarkets_account_id: 'd2605e89-7bc2-4144-9f7c-951edd596c39',
      mt5_libertex_real_account_id: '',
      swing_trading_enabled: true,
      swing_min_confidence_score: 0.6,
      swing_stop_loss_percent: 2.0,
      swing_take_profit_percent: 4.0,
      swing_max_positions: 5,
      swing_risk_per_trade_percent: 2.0,
      swing_position_hold_time_hours: 168,
      day_trading_enabled: true,
      day_min_confidence_score: 0.4,
      day_stop_loss_percent: 1.5,
      day_take_profit_percent: 2.5,
      day_max_positions: 10,
      day_risk_per_trade_percent: 1.0,
      day_position_hold_time_hours: 2,
      scalping_enabled: false,
      scalping_min_confidence_score: 0.6,
      scalping_max_positions: 3,
      scalping_take_profit_percent: 0.15,
      scalping_stop_loss_percent: 0.08,
      scalping_max_hold_time_minutes: 5,
      scalping_risk_per_trade_percent: 0.5,
      mean_reversion_enabled: false,
      mean_reversion_bollinger_period: 20,
      mean_reversion_bollinger_std: 2.0,
      mean_reversion_rsi_oversold: 30,
      mean_reversion_rsi_overbought: 70,
      mean_reversion_min_confidence: 0.65,
      mean_reversion_stop_loss_percent: 1.5,
      mean_reversion_take_profit_percent: 2.0,
      mean_reversion_max_positions: 5,
      mean_reversion_risk_per_trade_percent: 1.5,
      momentum_enabled: false,
      momentum_period: 14,
      momentum_threshold: 0.5,
      momentum_ma_fast_period: 50,
      momentum_ma_slow_period: 200,
      momentum_min_confidence: 0.7,
      momentum_stop_loss_percent: 2.5,
      momentum_take_profit_percent: 5.0,
      momentum_max_positions: 8,
      momentum_risk_per_trade_percent: 2.0,
      breakout_enabled: false,
      breakout_lookback_period: 20,
      breakout_confirmation_bars: 2,
      breakout_volume_multiplier: 1.5,
      breakout_min_confidence: 0.65,
      breakout_stop_loss_percent: 2.0,
      breakout_take_profit_percent: 4.0,
      breakout_max_positions: 6,
      breakout_risk_per_trade_percent: 1.8,
      grid_enabled: false,
      grid_size_pips: 50,
      grid_levels: 5,
      grid_direction: 'BOTH',
      grid_stop_loss_percent: 3.0,
      grid_tp_per_level_percent: 1.0,
      grid_max_positions: 10,
      grid_risk_per_trade_percent: 1.0,
    };

    setFormData({ ...defaults, ...settings });
    console.log('📋 SettingsDialog synced - active_platforms:', settings.active_platforms);
  }, [open, settings]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const validPlatforms = ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL', 'BITPANDA'];
    let activePlatforms = settings?.active_platforms || formData.active_platforms || [];
    activePlatforms = activePlatforms.filter((p) => validPlatforms.includes(p));
    if (activePlatforms.length === 0) {
      activePlatforms = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO'];
    }

    const settingsToSave = {
      ...formData,
      active_platforms: activePlatforms,
    };

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔍 FRONTEND: Sending settings to backend...');
    console.log('Day Trading:');
    console.log('  - day_stop_loss_percent:', settingsToSave.day_stop_loss_percent);
    console.log('  - day_take_profit_percent:', settingsToSave.day_take_profit_percent);
    console.log('Swing Trading:');
    console.log('  - swing_stop_loss_percent:', settingsToSave.swing_stop_loss_percent);
    console.log('  - swing_take_profit_percent:', settingsToSave.swing_take_profit_percent);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    onSave(settingsToSave);
  };

  const aiProviderModels = {
    emergent: ['gpt-5', 'gpt-4-turbo'],
    openai: ['gpt-5', 'gpt-4-turbo'],
    gemini: ['gemini-2.0-flash-exp', 'gemini-1.5-pro'],
    anthropic: ['claude-3-5-sonnet-20241022'],
    ollama: ['llama4', 'llama3.2', 'llama3.1', 'mistral', 'codellama'],
  };

  const currentProvider = formData.ai_provider || 'emergent';
  const availableModels = aiProviderModels[currentProvider] || ['gpt-5'];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">⚙️ Trading Bot Einstellungen</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-slate-800">
              <TabsTrigger value="general" className="data-[state=active]:bg-cyan-600">
                <Zap className="w-4 h-4 mr-2" />
                Allgemein
              </TabsTrigger>
              <TabsTrigger value="platforms" className="data-[state=active]:bg-cyan-600">
                <Cloud className="w-4 h-4 mr-2" />
                Plattformen
              </TabsTrigger>
              <TabsTrigger value="aibot" className="data-[state=active]:bg-cyan-600">
                <Activity className="w-4 h-4 mr-2" />
                AI Bot
              </TabsTrigger>
              <TabsTrigger value="risk" className="data-[state=active]:bg-cyan-600">
                <Shield className="w-4 h-4 mr-2" />
                Risiko Management
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Auto-Trading</h3>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="auto_trading" className="text-base font-medium">
                      Automatisches Trading aktivieren
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">Bot öffnet und schließt Trades automatisch</p>
                  </div>
                  <Switch
                    id="auto_trading"
                    checked={formData.auto_trading || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, auto_trading: checked })}
                  />
                </div>

                <div className="p-4 bg-slate-700 rounded-lg border border-slate-600">
                  <div className="mb-3">
                    <Label className="text-base font-medium">Trading-Modus</Label>
                    <p className="text-sm text-slate-400 mt-1">
                      {formData.trading_mode === 'aggressive'
                        ? '🔥 Aggressiv: Maximale Aktivität, niedrigste Thresholds'
                        : formData.trading_mode === 'neutral'
                        ? '⚖️ Neutral: Ausgewogene Balance zwischen Qualität und Aktivität'
                        : '🛡️ Konservativ: Höchste Qualität, weniger Trades'}
                    </p>
                  </div>

                  <div className="flex gap-2 p-1 bg-slate-800 rounded-lg">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, trading_mode: 'conservative' })}
                      className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                        formData.trading_mode === 'conservative'
                          ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/30'
                          : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                      }`}
                    >
                      🛡️ Konservativ
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, trading_mode: 'neutral' })}
                      className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                        formData.trading_mode === 'neutral'
                          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                          : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                      }`}
                    >
                      ⚖️ Neutral
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, trading_mode: 'aggressive' })}
                      className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                        formData.trading_mode === 'aggressive'
                          ? 'bg-orange-600 text-white shadow-lg shadow-orange-500/30'
                          : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                      }`}
                    >
                      🔥 Aggressiv
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-slate-900 rounded-lg text-xs">
                  <div className="text-slate-400 mb-2 font-medium">
                    Confidence-Thresholds ({
                      formData.trading_mode === 'aggressive' ? '🔥 Aggressiv' :
                      formData.trading_mode === 'neutral' ? '⚖️ Neutral' :
                      '🛡️ Konservativ'
                    }):
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-slate-500">
                    <span>• Starker Trend: {formData.trading_mode === 'aggressive' ? '55%' : formData.trading_mode === 'neutral' ? '62%' : '70%'}</span>
                    <span>• Normal Trend: {formData.trading_mode === 'aggressive' ? '58%' : formData.trading_mode === 'neutral' ? '65%' : '72%'}</span>
                    <span>• Range: {formData.trading_mode === 'aggressive' ? '60%' : formData.trading_mode === 'neutral' ? '68%' : '75%'}</span>
                    <span>• High Vola: {formData.trading_mode === 'aggressive' ? '65%' : formData.trading_mode === 'neutral' ? '72%' : '80%'}</span>
                    <span>• Chaos: {formData.trading_mode === 'aggressive' ? '72%' : formData.trading_mode === 'neutral' ? '80%' : '88%'}</span>
                    <span className="font-medium text-cyan-400">• Minimum: {formData.trading_mode === 'aggressive' ? '60%' : formData.trading_mode === 'neutral' ? '68%' : '75%'}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Handelszeiten</h3>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="respect_market_hours" className="text-base font-medium">
                      Markt-Öffnungszeiten beachten
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">Bot handelt nur während Marktöffnungszeiten</p>
                  </div>
                  <Switch
                    id="respect_market_hours"
                    checked={formData.respect_market_hours !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, respect_market_hours: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="allow_weekend_trading" className="text-base font-medium">
                      Wochenend-Trading erlauben
                    </Label>
                  </div>
                  <Switch
                    id="allow_weekend_trading"
                    checked={formData.allow_weekend_trading || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, allow_weekend_trading: checked })}
                  />
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">🔔 Auto-Close (Gewinn-Sicherung)</h3>
                <p className="text-sm text-slate-400 mb-4">Automatisches Schließen von Positionen im Plus vor Handelsschluss</p>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="auto_close_profitable_daily" className="text-base font-medium">
                      📅 Tägliches Auto-Close
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">Schließt profitable Intraday-Trades vor Handelsschluss</p>
                    <p className="text-xs text-amber-400 mt-1">⚡ Nur Day-Trading, Scalping, Momentum, Mean Reversion</p>
                  </div>
                  <Switch
                    id="auto_close_profitable_daily"
                    checked={formData.auto_close_profitable_daily !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, auto_close_profitable_daily: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="auto_close_all_friday" className="text-base font-medium">
                      🗓️ Freitag Auto-Close (Wochenend-Schutz)
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">Schließt ALLE profitablen Trades vor Wochenende</p>
                    <p className="text-xs text-emerald-400 mt-1">✅ Inkl. Swing, Grid, Breakout - Verhindert Wochenend-Gaps</p>
                  </div>
                  <Switch
                    id="auto_close_all_friday"
                    checked={formData.auto_close_all_friday !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, auto_close_all_friday: checked })}
                  />
                </div>

                <div className="p-4 bg-slate-700 rounded-lg">
                  <Label htmlFor="auto_close_minutes_before" className="text-base font-medium">
                    ⏱️ Minuten vor Handelsschluss
                  </Label>
                  <p className="text-sm text-slate-400 mt-1 mb-3">Wie viele Minuten vor Schließung sollen Trades beendet werden?</p>
                  <Input
                    id="auto_close_minutes_before"
                    type="number"
                    min="1"
                    max="60"
                    value={formData.auto_close_minutes_before || 10}
                    onChange={(e) => setFormData({ ...formData, auto_close_minutes_before: parseInt(e.target.value) || 10 })}
                    className="w-24 bg-slate-800 border-slate-600"
                  />
                </div>
              </div>

              <MarketHoursManager formData={formData} setFormData={setFormData} />
            </TabsContent>

            <TabsContent value="platforms" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-cyan-400">MetaAPI Account IDs</h3>
                  <Button
                    type="button"
                    onClick={async () => {
                      try {
                        const API_URL = process.env.REACT_APP_BACKEND_URL || '';
                        const response = await fetch(`${API_URL}/metaapi/update-ids`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            libertex_demo_id: formData.mt5_libertex_account_id || '',
                            icmarkets_demo_id: formData.mt5_icmarkets_account_id || '',
                            libertex_real_id: formData.mt5_libertex_real_account_id || '',
                          }),
                        });

                        if (response.ok) {
                          alert('✅ MetaAPI IDs erfolgreich aktualisiert!');
                          window.location.reload();
                        } else {
                          const error = await response.json();
                          alert(`❌ Fehler: ${error.detail || 'Unbekannter Fehler'}`);
                        }
                      } catch (error) {
                        alert(`❌ Fehler: ${error.message}`);
                      }
                    }}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    🔄 IDs übernehmen & neu verbinden
                  </Button>
                </div>

                <div className="p-4 bg-blue-900/20 border border-blue-700 rounded-lg mb-4">
                  <p className="text-sm text-blue-200">
                    <strong>ℹ️ Hinweis:</strong> Tragen Sie hier Ihre MetaAPI Account IDs ein.
                    Nach dem Klick auf "IDs übernehmen" werden diese in beiden .env Dateien gespeichert
                    und die Verbindungen neu aufgebaut.
                  </p>
                </div>

                <div className="space-y-2 p-4 bg-slate-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="libertex_demo_id" className="text-base font-medium text-cyan-300">
                      🔷 MT5 Libertex Demo (MT5-510038543)
                    </Label>
                    <span className="text-xs text-slate-400">DEMO</span>
                  </div>
                  <Input
                    id="libertex_demo_id"
                    type="text"
                    placeholder="5cc9abd1-671a-447e-ab93-5abbfe0ed941"
                    value={formData.mt5_libertex_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_libertex_account_id: e.target.value })}
                    className="bg-slate-600 border-slate-500 font-mono text-sm"
                  />
                  <p className="text-xs text-slate-400 mt-1">Default: 5cc9abd1-671a-447e-ab93-5abbfe0ed941</p>
                </div>

                <div className="space-y-2 p-4 bg-slate-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="icmarkets_demo_id" className="text-base font-medium text-purple-300">
                      🟣 MT5 ICMarkets Demo (MT5-52565616)
                    </Label>
                    <span className="text-xs text-slate-400">DEMO</span>
                  </div>
                  <Input
                    id="icmarkets_demo_id"
                    type="text"
                    placeholder="d2605e89-7bc2-4144-9f7c-951edd596c39"
                    value={formData.mt5_icmarkets_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_icmarkets_account_id: e.target.value })}
                    className="bg-slate-600 border-slate-500 font-mono text-sm"
                  />
                  <p className="text-xs text-slate-400 mt-1">Default: d2605e89-7bc2-4144-9f7c-951edd596c39</p>
                </div>

                <div className="space-y-2 p-4 bg-amber-900/30 border border-amber-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="libertex_real_id" className="text-base font-medium text-amber-300">
                      💰 MT5 Libertex REAL (MT5-560031700)
                    </Label>
                    <span className="text-xs text-amber-400 font-bold">ECHTES GELD!</span>
                  </div>
                  <Input
                    id="libertex_real_id"
                    type="text"
                    placeholder="Noch nicht konfiguriert"
                    value={formData.mt5_libertex_real_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_libertex_real_account_id: e.target.value })}
                    className="bg-slate-600 border-amber-500 font-mono text-sm"
                  />
                  <p className="text-xs text-amber-300 mt-1">⚠️ Achtung: Dies ist ein ECHTGELD-Account! Nur aktivieren wenn Sie bereit für Live-Trading sind.</p>
                </div>

                <div className="p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg mt-4">
                  <p className="text-sm text-yellow-200">
                    <strong>📖 Anleitung:</strong><br />
                    1. Gehen Sie zu <a href="https://app.metaapi.cloud" target="_blank" rel="noopener noreferrer" className="underline">metaapi.cloud</a><br />
                    2. Wählen Sie Ihren Account aus<br />
                    3. Kopieren Sie die Account ID (lange UUID)<br />
                    4. Fügen Sie sie hier ein<br />
                    5. Klicken Sie auf "IDs übernehmen & neu verbinden"
                  </p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="aibot" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">KI-Analyse</h3>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <Label htmlFor="use_ai_analysis" className="text-base">KI-Analyse verwenden</Label>
                  <Switch
                    id="use_ai_analysis"
                    checked={formData.use_ai_analysis !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, use_ai_analysis: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ai_provider">AI Provider</Label>
                    <select
                      id="ai_provider"
                      value={currentProvider}
                      onChange={(e) => {
                        const newProvider = e.target.value;
                        const newModel = aiProviderModels[newProvider][0];
                        setFormData({ ...formData, ai_provider: newProvider, ai_model: newModel });
                      }}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100"
                    >
                      {Object.keys(aiProviderModels).map((provider) => (
                        <option key={provider} value={provider}>
                          {provider}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="ai_model">AI Model</Label>
                    <select
                      id="ai_model"
                      value={formData.ai_model || availableModels[0]}
                      onChange={(e) => setFormData({ ...formData, ai_model: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100"
                    >
                      {availableModels.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {currentProvider === 'ollama' && (
                  <div className="space-y-2">
                    <Label htmlFor="ollama_base_url">Ollama Server URL</Label>
                    <Input
                      id="ollama_base_url"
                      type="text"
                      placeholder="http://localhost:11434"
                      value={formData.ollama_base_url || 'http://localhost:11434'}
                      onChange={(e) => setFormData({ ...formData, ollama_base_url: e.target.value })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-400">URL des lokalen Ollama Servers (Standard: http://localhost:11434)</p>
                  </div>
                )}

                {currentProvider === 'openai' && (
                  <div className="space-y-2">
                    <Label htmlFor="openai_api_key">OpenAI API Key</Label>
                    <Input
                      id="openai_api_key"
                      type="password"
                      placeholder="sk-..."
                      value={formData.openai_api_key || ''}
                      onChange={(e) => setFormData({ ...formData, openai_api_key: e.target.value })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-400">
                      Erhalten Sie Ihren API Key von <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">platform.openai.com</a>
                    </p>
                  </div>
                )}

                {currentProvider === 'gemini' && (
                  <div className="space-y-2">
                    <Label htmlFor="gemini_api_key">Google Gemini API Key</Label>
                    <Input
                      id="gemini_api_key"
                      type="password"
                      placeholder="AI..."
                      value={formData.gemini_api_key || ''}
                      onChange={(e) => setFormData({ ...formData, gemini_api_key: e.target.value })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-400">
                      Erhalten Sie Ihren API Key von <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">aistudio.google.com</a>
                    </p>
                  </div>
                )}

                {currentProvider === 'anthropic' && (
                  <div className="space-y-2">
                    <Label htmlFor="anthropic_api_key">Anthropic Claude API Key</Label>
                    <Input
                      id="anthropic_api_key"
                      type="password"
                      placeholder="sk-ant-..."
                      value={formData.anthropic_api_key || ''}
                      onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-400">
                      Erhalten Sie Ihren API Key von <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">console.anthropic.com</a>
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="use_llm_confirmation" className="text-base">LLM Final Confirmation</Label>
                    <p className="text-sm text-slate-400 mt-1">LLM prüft jedes Signal vor Trade-Ausführung</p>
                  </div>
                  <Switch
                    id="use_llm_confirmation"
                    checked={formData.use_llm_confirmation || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, use_llm_confirmation: checked })}
                  />
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Technische Indikatoren</h3>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rsi_oversold">RSI Überverkauft</Label>
                    <Input
                      id="rsi_oversold"
                      type="number"
                      value={formData.rsi_oversold_threshold || 30}
                      onChange={(e) => setFormData({ ...formData, rsi_oversold_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="rsi_overbought">RSI Überkauft</Label>
                    <Input
                      id="rsi_overbought"
                      type="number"
                      value={formData.rsi_overbought_threshold || 70}
                      onChange={(e) => setFormData({ ...formData, rsi_overbought_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="macd_threshold">MACD Schwelle</Label>
                    <Input
                      id="macd_threshold"
                      type="number"
                      step="0.01"
                      value={formData.macd_signal_threshold || 0}
                      onChange={(e) => setFormData({ ...formData, macd_signal_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="risk" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Globale Limits</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max_trades_hour">Max. Trades pro Stunde</Label>
                    <Input
                      id="max_trades_hour"
                      type="number"
                      value={formData.max_trades_per_hour || 10}
                      onChange={(e) => setFormData({ ...formData, max_trades_per_hour: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max_balance_percent">Max. Balance-Nutzung pro Plattform (%)</Label>
                    <Input
                      id="max_balance_percent"
                      type="number"
                      step="0.1"
                      value={formData.combined_max_balance_percent_per_platform || 20.0}
                      onChange={(e) => setFormData({ ...formData, combined_max_balance_percent_per_platform: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>

                <div className="p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg">
                  <p className="text-sm text-yellow-200">
                    <strong>⚠️ Wichtig:</strong> Diese Limits schützen Ihr Kapital. Der Bot wird keine Trades öffnen,
                    wenn diese Limits erreicht sind.
                  </p>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex gap-4 justify-end pt-4 border-t border-slate-700">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Abbrechen
            </Button>
            <Button type="submit" className="bg-cyan-600 hover:bg-cyan-700">
              Einstellungen speichern
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default SettingsDialog;

const MarketHoursManager = ({ formData, setFormData }) => {
  const [marketHours, setMarketHours] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const API_URL = process.env.REACT_APP_BACKEND_URL || '';

  const commodityCount = Object.keys(marketHours || {}).length;
  const enabledCount = Object.values(marketHours || {}).filter((asset) => asset.enabled !== false).length;

  useEffect(() => {
    fetchMarketHours();
  }, []);

  const fetchMarketHours = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/market/hours/all`);
      if (response.data.success) {
        setMarketHours(response.data.market_hours || {});
      }
    } catch (error) {
      console.error('Error fetching market hours:', error);
      toast.error('Fehler beim Laden der Handelszeiten');
    } finally {
      setLoading(false);
    }
  };

  const updateAssetHours = (assetId, field, value) => {
    setMarketHours((prev) => ({
      ...prev,
      [assetId]: {
        ...prev[assetId],
        [field]: value,
      },
    }));
  };

  const toggleDay = (assetId, day) => {
    const currentDays = marketHours[assetId]?.days || [];
    const newDays = currentDays.includes(day)
      ? currentDays.filter((d) => d !== day)
      : [...currentDays, day].sort();
    updateAssetHours(assetId, 'days', newDays);
  };

  const applyPreset = (assetId, preset) => {
    // Asset-spezifische Handelszeiten nach Libertex
    const assetPresets = {
        // Forex-Paare (alle identisch)
        USDJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        GBPUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        EURUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        AUDUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        USDCHF:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        USDCAD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        NZDUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        EURGBP:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        EURJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        GBPJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        AUDJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        CHFJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        CADJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        AUDCAD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        AUDNZD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        EURNZD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        EURAUD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
        GBPAUD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      // Edelmetalle
      GOLD:      { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      SILVER:    { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      PLATINUM:  { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      PALLADIUM: { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      // Industriemetalle
      COPPER:    { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      ZINC:      { enabled: true, days: [0,1,2,3,4], open_time: '02:00', close_time: '22:00', description: 'Mo 02:00 – Fr 22:00 (MEZ/MESZ)' },
      // Energie
      WTI_CRUDE:    { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      BRENT_CRUDE:  { enabled: true, days: [0,1,2,3,4], open_time: '02:00', close_time: '23:00', description: 'Mo 02:00 – Fr 23:00 (MEZ/MESZ)' },
      NATURAL_GAS:  { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      // Agrarrohstoffe
      WHEAT:     { enabled: true, days: [0,1,2,3,4], open_time: '02:00', close_time: '20:45', description: 'Mo 02:00 – Fr 20:45 (MEZ/MESZ)' },
      CORN:      { enabled: true, days: [0,1,2,3,4], open_time: '02:00', close_time: '20:45', description: 'Mo 02:00 – Fr 20:45 (MEZ/MESZ)' },
      SOYBEANS:  { enabled: true, days: [0,1,2,3,4], open_time: '02:00', close_time: '20:45', description: 'Mo 02:00 – Fr 20:45 (MEZ/MESZ)' },
      COFFEE:    { enabled: true, days: [0,1,2,3,4], open_time: '10:15', close_time: '18:30', description: 'Mo 10:15 – Fr 18:30 (MEZ/MESZ)' },
      SUGAR:     { enabled: true, days: [0,1,2,3,4], open_time: '09:00', close_time: '18:00', description: 'Mo 09:00 – Fr 18:00 (MEZ/MESZ)' },
      COCOA:     { enabled: true, days: [0,1,2,3,4], open_time: '10:45', close_time: '19:30', description: 'Mo 10:45 – Fr 19:30 (MEZ/MESZ)' },
      // Forex (alle Paare)
      USDJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      GBPUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      EURUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      AUDUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      USDCHF:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      USDCAD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      NZDUSD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      EURGBP:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      EURJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      GBPJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      AUDJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      CHFJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      CADJPY:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      AUDCAD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      AUDNZD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      EURNZD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      EURAUD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      GBPAUD:    { enabled: true, days: [0,1,2,3,4], open_time: '00:05', close_time: '23:55', description: 'Mo 00:05 – Fr 23:55 (MEZ/MESZ)' },
      // US-Indizes
      SP500:        { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      DOWJONES30:   { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      NASDAQ100:    { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      RUSSELL2000:  { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      VIX:          { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      // EU-Indizes
      DAX40:        { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      FTSE100:      { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      EUROSTOXX50:  { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      CAC40:        { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      IBEX35:       { enabled: true, days: [0,1,2,3,4], open_time: '09:00', close_time: '17:30', description: 'Mo 09:00 – Fr 17:30 (MEZ/MESZ)' },
      SMI20:        { enabled: true, days: [0,1,2,3,4], open_time: '09:00', close_time: '17:30', description: 'Mo 09:00 – Fr 17:30 (MEZ/MESZ)' },
      AEX25:        { enabled: true, days: [0,1,2,3,4], open_time: '09:00', close_time: '17:30', description: 'Mo 09:00 – Fr 17:30 (MEZ/MESZ)' },
      // Asien-Indizes
      NIKKEI225:    { enabled: true, days: [0,1,2,3,4], open_time: '01:00', close_time: '23:00', description: 'Mo 01:00 – Fr 23:00 (MEZ/MESZ)' },
      HANGSENG50:   { enabled: true, days: [0,1,2,3,4], open_time: '02:15', close_time: '21:00', description: 'Mo 02:15 – Fr 21:00 (MEZ/MESZ)' },
      ASX200:       { enabled: true, days: [0,1,2,3,4], open_time: '00:50', close_time: '22:00', description: 'Mo 00:50 – Fr 22:00 (MEZ/MESZ)' },
      // Krypto
      BITCOIN:      { enabled: true, days: [0,1,2,3,4,5,6], open_time: '00:00', close_time: '23:59', description: '24/7' },
      ETHEREUM:     { enabled: true, days: [0,1,2,3,4,5,6], open_time: '00:00', close_time: '23:59', description: '24/7' },
    };

    // Standardpresets für generische Buttons
    const presets = {
      '24_7': {
        enabled: true,
        days: [0, 1, 2, 3, 4, 5, 6],
        open_time: '00:00',
        close_time: '23:59',
        is_24_7: true,
        is_24_5: false,
        description: '24/7 - Immer geöffnet',
      },
      '24_5': {
        enabled: true,
        days: [0, 1, 2, 3, 4],
        open_time: '22:00',
        close_time: '21:00',
        is_24_5: true,
        is_24_7: false,
        description: '24/5 - Sonntag 22:00 bis Freitag 21:00 UTC',
      },
      boerse: {
        enabled: true,
        days: [0, 1, 2, 3, 4],
        open_time: '08:30',
        close_time: '20:00',
        is_24_5: false,
        is_24_7: false,
        description: 'Börsenzeiten Mo-Fr 08:30-20:00 UTC',
      },
    };

    // Wenn Asset ein bekanntes Preset hat, dieses anwenden
    const assetKey = assetId.toUpperCase();
    if (preset === 'boerse' && assetPresets[assetKey]) {
      setMarketHours((prev) => ({
        ...prev,
        [assetId]: {
          ...prev[assetId],
          ...assetPresets[assetKey],
        },
      }));
    } else {
      setMarketHours((prev) => ({
        ...prev,
        [assetId]: {
          ...prev[assetId],
          ...presets[preset],
        },
      }));
    }
  };

  const saveAllMarketHours = async () => {
    setSaving(true);
    try {
      const promises = Object.keys(marketHours).map((assetId) =>
        axios.post(`${API_URL}/api/market/hours/update`, {
          commodity_id: assetId,
          hours_config: marketHours[assetId],
        })
      );
      await Promise.all(promises);
      toast.success('Handelszeiten erfolgreich gespeichert!');
    } catch (error) {
      console.error('Error saving market hours:', error);
      toast.error('Fehler beim Speichern der Handelszeiten');
    } finally {
      setSaving(false);
    }
  };

  const groupedAssets = Object.entries(marketHours).reduce((acc, [assetId, config]) => {
    const category = config.commodity_category || 'Andere';
    if (!acc[category]) acc[category] = [];
    acc[category].push({ id: assetId, ...config });
    return acc;
  }, {});

  const dayNames = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  if (loading) {
    return <div className="text-center text-slate-400 py-4">Lade Handelszeiten...</div>;
  }

  return (
    <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
            <Clock className="w-5 h-5" />
            <span>Handelszeiten (Asset-spezifisch)</span>
          </h3>
          <p className="text-sm text-slate-400 mt-1">Legen Sie für jedes Asset individuelle Handelszeiten fest.</p>
        </div>
        <Button onClick={saveAllMarketHours} disabled={saving} className="bg-green-600 hover:bg-green-500" size="sm">
          {saving ? 'Speichert...' : 'Alle Speichern'}
        </Button>
      </div>

      <div className="flex items-center justify-between p-3 bg-slate-700 rounded border border-slate-600">
        <div>
          <Label className="text-sm font-semibold">Handelszeiten-System aktivieren</Label>
          <p className="text-xs text-slate-300 mt-1">Bot respektiert die definierten Zeiten für jedes Asset</p>
        </div>
        <Switch
          checked={formData.respect_market_hours !== false}
          onCheckedChange={(checked) => setFormData({ ...formData, respect_market_hours: checked })}
        />
      </div>

      {formData.respect_market_hours !== false && (
        <div className="space-y-6 mt-4">
          <div className={`p-3 rounded border ${commodityCount === 50 ? 'border-emerald-700 bg-emerald-900/20' : 'border-amber-600 bg-amber-900/20'}`}>
            <div className="text-sm text-slate-200 font-semibold flex items-center justify-between">
              <span>Geladene Assets: {commodityCount} / 50</span>
              <span>Aktiv ausgewählt: {enabledCount}</span>
            </div>
            {commodityCount !== 50 && (
              <p className="text-xs text-amber-300 mt-1">Hinweis: Backend oder Cache liefert nicht alle 50 Assets. Bitte Backend prüfen oder App neu starten.</p>
            )}
          </div>

          {Object.entries(groupedAssets).length === 0 && (
            <p className="text-xs text-slate-400">Keine Asset-Daten geladen. Bitte Backend prüfen oder App neu laden.</p>
          )}

          {Object.entries(groupedAssets).map(([category, assets]) => (
            <div key={category} className="space-y-3">
              <h5 className="font-semibold text-md text-cyan-300 flex items-center gap-2 border-b border-slate-700 pb-2">
                <span>{category}</span>
                <span className="text-xs text-slate-500">({assets.length})</span>
              </h5>

              {assets.map((asset) => (
                <div key={asset.id} className="p-4 bg-slate-700/60 rounded border border-slate-600/70 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-sm font-semibold text-slate-200">{asset.commodity_name || asset.id}</Label>
                      <p className="text-xs text-slate-400">{asset.id}</p>
                    </div>
                    <Switch
                      checked={asset.enabled !== false}
                      onCheckedChange={(checked) => updateAssetHours(asset.id, 'enabled', checked)}
                    />
                  </div>

                  {asset.enabled !== false && (
                    <>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, '24_7')}
                          className="px-3 py-1 text-xs rounded bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-600/50"
                        >
                          24/7
                        </button>
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, '24_5')}
                          className="px-3 py-1 text-xs rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-600/50"
                        >
                          24/5
                        </button>
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, 'boerse')}
                          className="px-3 py-1 text-xs rounded bg-orange-600/20 hover:bg-orange-600/40 text-orange-300 border border-orange-600/50"
                        >
                          Börse (08:30-20:00)
                        </button>
                      </div>

                      <div>
                        <Label className="text-xs text-slate-300 mb-2 block">Handelstage:</Label>
                        <div className="flex gap-2">
                          {dayNames.map((day, index) => {
                            const isActive = asset.days?.includes(index);
                            return (
                              <button
                                key={index}
                                type="button"
                                onClick={() => toggleDay(asset.id, index)}
                                className={`px-3 py-1 text-xs rounded transition-colors ${
                                  isActive
                                    ? 'bg-green-600 text-white'
                                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                                }`}
                              >
                                {day}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-xs text-slate-300">Öffnungszeit (UTC)</Label>
                          <Input
                            type="time"
                            value={asset.open_time || '00:00'}
                            onChange={(e) => updateAssetHours(asset.id, 'open_time', e.target.value)}
                            className="bg-slate-800 border-slate-700 text-sm"
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-slate-300">Schließzeit (UTC)</Label>
                          <Input
                            type="time"
                            value={asset.close_time || '23:59'}
                            onChange={(e) => updateAssetHours(asset.id, 'close_time', e.target.value)}
                            className="bg-slate-800 border-slate-700 text-sm"
                          />
                        </div>
                      </div>

                      <div className="text-xs text-slate-400 italic">{asset.description}</div>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <div className="p-3 bg-blue-900/20 border border-blue-700/50 rounded">
        <p className="text-xs text-blue-300 flex items-center gap-2">
          <span>ℹ️</span>
          <span>
            <strong>Hinweis:</strong> Alle Zeiten in UTC. Der AI Bot öffnet keine neuen Trades außerhalb der definierten Zeiten. Änderungen werden erst nach "Alle Speichern" aktiv.
          </span>
        </p>
      </div>
    </div>
  );
};
