/**
 * SettingsPanel Component
 * Manages reading preferences: font size, theme, line height, font family
 * Changes are immediately reflected in the reader via state manager
 */

import React, { useState, useEffect } from 'react';
import { ReaderStateManager } from '@/reader/state';
import { ReadingPreferences } from '@/reader/types';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onPreferenceChange: (preferences: Partial<ReadingPreferences>) => void;
  stateManager: ReaderStateManager | null;
}

/**
 * SettingsPanel Component
 */
export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  isOpen,
  onClose,
  onPreferenceChange,
  stateManager,
}) => {
  const [preferences, setPreferences] = useState<ReadingPreferences | null>(null);

  /**
   * Load initial preferences from state manager
   */
  useEffect(() => {
    if (stateManager) {
      const state = stateManager.getState();
      setPreferences(state.preferences);
    }
  }, [stateManager]);

  /**
   * Handle font size change
   */
  const handleFontSizeChange = (size: number) => {
    if (preferences) {
      const newPrefs = { ...preferences, fontSize: size };
      setPreferences(newPrefs);
      onPreferenceChange({ fontSize: size });
    }
  };

  /**
   * Handle theme change
   */
  const handleThemeChange = (theme: 'light' | 'dark' | 'sepia') => {
    if (preferences) {
      const newPrefs = { ...preferences, theme };
      setPreferences(newPrefs);
      onPreferenceChange({ theme });

      // Update DOM theme attribute
      const container = document.querySelector('.reader-container');
      if (container) {
        container.setAttribute('data-theme', theme);
      }
    }
  };

  /**
   * Handle line height change
   */
  const handleLineHeightChange = (lineHeight: 'small' | 'medium' | 'large') => {
    if (preferences) {
      const newPrefs = { ...preferences, lineHeight };
      setPreferences(newPrefs);
      onPreferenceChange({ lineHeight });
    }
  };

  /**
   * Handle font family change
   */
  const handleFontFamilyChange = (fontFamily: 'serif' | 'sans-serif' | 'monospace') => {
    if (preferences) {
      const newPrefs = { ...preferences, fontFamily };
      setPreferences(newPrefs);
      onPreferenceChange({ fontFamily });
    }
  };

  /**
   * Handle image scale change
   */
  const handleImageScaleChange = (scale: number) => {
    if (preferences) {
      const newPrefs = { ...preferences, imageScale: scale };
      setPreferences(newPrefs);
      onPreferenceChange({ imageScale: scale });
    }
  };

  /**
   * Handle formula size change
   */
  const handleFormulaSizeChange = (size: number) => {
    if (preferences) {
      const newPrefs = { ...preferences, formulaSize: size };
      setPreferences(newPrefs);
      onPreferenceChange({ formulaSize: size });
    }
  };

  if (!isOpen || !preferences) {
    return null;
  }

  return (
    <div className="reader-settings-overlay" onClick={onClose}>
      <div
        className="reader-settings-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="reader-settings-header">
          <h2>Reading Preferences</h2>
          <button className="reader-settings-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="reader-settings-content">
          {/* Font Size */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Font Size</label>
            <div className="reader-settings-value">{preferences.fontSize}px</div>
            <input
              type="range"
              className="reader-slider"
              min="14"
              max="28"
              value={preferences.fontSize}
              onChange={(e) => handleFontSizeChange(parseInt(e.target.value))}
            />
            <div className="reader-settings-hint">14px - 28px</div>
          </div>

          {/* Theme */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Theme</label>
            <div className="reader-settings-buttons">
              {(['light', 'dark', 'sepia'] as const).map((theme) => (
                <button
                  key={theme}
                  className={`reader-settings-button ${
                    preferences.theme === theme ? 'active' : ''
                  }`}
                  onClick={() => handleThemeChange(theme)}
                >
                  {theme === 'light' && '☀️'}
                  {theme === 'dark' && '🌙'}
                  {theme === 'sepia' && '📖'}
                  <span>{theme.charAt(0).toUpperCase() + theme.slice(1)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Line Height */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Line Height</label>
            <div className="reader-settings-buttons">
              {(['small', 'medium', 'large'] as const).map((lh) => (
                <button
                  key={lh}
                  className={`reader-settings-button ${
                    preferences.lineHeight === lh ? 'active' : ''
                  }`}
                  onClick={() => handleLineHeightChange(lh)}
                >
                  {lh === 'small' && '↕'}
                  {lh === 'medium' && '⟷'}
                  {lh === 'large' && '⇕'}
                  <span>{lh.charAt(0).toUpperCase() + lh.slice(1)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Font Family */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Font Family</label>
            <div className="reader-settings-buttons">
              {(['serif', 'sans-serif', 'monospace'] as const).map((font) => (
                <button
                  key={font}
                  className={`reader-settings-button ${
                    preferences.fontFamily === font ? 'active' : ''
                  }`}
                  onClick={() => handleFontFamilyChange(font)}
                  style={{
                    fontFamily:
                      font === 'serif'
                        ? 'Georgia, serif'
                        : font === 'sans-serif'
                          ? 'Segoe UI, sans-serif'
                          : 'Courier New, monospace',
                  }}
                >
                  {font === 'serif' && 'Serif'}
                  {font === 'sans-serif' && 'Sans'}
                  {font === 'monospace' && 'Mono'}
                </button>
              ))}
            </div>
          </div>

          {/* Image Scale */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Image Scale</label>
            <div className="reader-settings-value">
              {Math.round((preferences.imageScale || 1) * 100)}%
            </div>
            <input
              type="range"
              className="reader-slider"
              min="0.5"
              max="1.5"
              step="0.1"
              value={preferences.imageScale || 1}
              onChange={(e) => handleImageScaleChange(parseFloat(e.target.value))}
            />
            <div className="reader-settings-hint">50% - 150%</div>
          </div>

          {/* Formula Size */}
          <div className="reader-settings-group">
            <label className="reader-settings-label">Formula Size</label>
            <div className="reader-settings-value">
              {Math.round((preferences.formulaSize || 1) * 100)}%
            </div>
            <input
              type="range"
              className="reader-slider"
              min="0.8"
              max="1.2"
              step="0.1"
              value={preferences.formulaSize || 1}
              onChange={(e) => handleFormulaSizeChange(parseFloat(e.target.value))}
            />
            <div className="reader-settings-hint">80% - 120%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
