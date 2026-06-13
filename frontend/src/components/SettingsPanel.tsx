import React, { useState, useEffect } from 'react';
import { ReaderTheme } from '../reader/types';

interface SettingsPanelProps {
    currentTheme: ReaderTheme;
    currentFontSize: number;
    currentLineHeight: 'small' | 'medium' | 'large';
    currentFontFamily: 'serif' | 'sans-serif' | 'monospace';
    currentImageScale: number;
    currentFormulaSize: number;
    onThemeChange: (theme: ReaderTheme) => void;
    onFontSizeChange: (size: number) => void;
    onLineHeightChange: (height: 'small' | 'medium' | 'large') => void;
    onFontFamilyChange: (font: 'serif' | 'sans-serif' | 'monospace') => void;
    onImageScaleChange: (scale: number) => void;
    onFormulaSizeChange: (size: number) => void;
    isOpen: boolean;
    onClose: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({
    currentTheme,
    currentFontSize,
    currentLineHeight,
    currentFontFamily,
    currentImageScale,
    currentFormulaSize,
    onThemeChange,
    onFontSizeChange,
    onLineHeightChange,
    onFontFamilyChange,
    onImageScaleChange,
    onFormulaSizeChange,
    isOpen,
    onClose,
}) => {
    const [theme, setTheme] = useState<ReaderTheme>(currentTheme);
    const [fontSize, setFontSize] = useState<number>(currentFontSize);
    const [lineHeight, setLineHeight] = useState<'small' | 'medium' | 'large'>(currentLineHeight);
    const [fontFamily, setFontFamily] = useState<'serif' | 'sans-serif' | 'monospace'>(currentFontFamily);
    const [imageScale, setImageScale] = useState<number>(currentImageScale);
    const [formulaSize, setFormulaSize] = useState<number>(currentFormulaSize);

    useEffect(() => {
        setTheme(currentTheme);
        setFontSize(currentFontSize);
        setLineHeight(currentLineHeight);
        setFontFamily(currentFontFamily);
        setImageScale(currentImageScale);
        setFormulaSize(currentFormulaSize);
    }, [currentTheme, currentFontSize, currentLineHeight, currentFontFamily, currentImageScale, currentFormulaSize]);

    const handleThemeChange = (newTheme: ReaderTheme) => {
        setTheme(newTheme);
        onThemeChange(newTheme);
    };

    const handleFontSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newSize = parseInt(e.target.value);
        setFontSize(newSize);
        onFontSizeChange(newSize);
    };

    const handleLineHeightChange = (newHeight: 'small' | 'medium' | 'large') => {
        setLineHeight(newHeight);
        onLineHeightChange(newHeight);
    };

    const handleFontFamilyChange = (newFont: 'serif' | 'sans-serif' | 'monospace') => {
        setFontFamily(newFont);
        onFontFamilyChange(newFont);
    };

    const handleImageScaleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newScale = parseFloat(e.target.value);
        setImageScale(newScale);
        onImageScaleChange(newScale);
    };

    const handleFormulaSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newSize = parseFloat(e.target.value);
        setFormulaSize(newSize);
        onFormulaSizeChange(newSize);
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div className="reader-settings-overlay" onClick={onClose}>
            <div className="reader-settings-panel" onClick={(e) => e.stopPropagation()}>
                <div className="reader-settings-header">
                    <h2>Reading Preferences</h2>
                    <button className="reader-settings-close" onClick={onClose}>✕</button>
                </div>
                <div className="reader-settings-content">
                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Font Size</label>
                        <div className="reader-settings-value">{fontSize}px</div>
                        <input
                            type="range"
                            className="reader-slider"
                            min="14"
                            max="28"
                            value={fontSize}
                            onChange={handleFontSizeChange}
                        />
                        <div className="reader-settings-hint">14px - 28px</div>
                    </div>

                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Theme</label>
                        <div className="reader-settings-buttons">
                            {(['light', 'dark', 'sepia'] as const).map((t) => (
                                <button
                                    key={t}
                                    className={`reader-settings-button ${theme === t ? 'active' : ''}`}
                                    onClick={() => handleThemeChange(t)}
                                >
                                    {t === 'light' && '☀️'}
                                    {t === 'dark' && '🌙'}
                                    {t === 'sepia' && '📖'}
                                    <span>{t.charAt(0).toUpperCase() + t.slice(1)}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Line Height</label>
                        <div className="reader-settings-buttons">
                            {(['small', 'medium', 'large'] as const).map((lh) => (
                                <button
                                    key={lh}
                                    className={`reader-settings-button ${lineHeight === lh ? 'active' : ''}`}
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

                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Font Family</label>
                        <div className="reader-settings-buttons">
                            {(['serif', 'sans-serif', 'monospace'] as const).map((font) => (
                                <button
                                    key={font}
                                    className={`reader-settings-button ${fontFamily === font ? 'active' : ''}`}
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

                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Image Scale</label>
                        <div className="reader-settings-value">{Math.round(imageScale * 100)}%</div>
                        <input
                            type="range"
                            className="reader-slider"
                            min="0.5"
                            max="1.5"
                            step="0.1"
                            value={imageScale}
                            onChange={handleImageScaleChange}
                        />
                        <div className="reader-settings-hint">50% - 150%</div>
                    </div>

                    <div className="reader-settings-group">
                        <label className="reader-settings-label">Formula Size</label>
                        <div className="reader-settings-value">{Math.round(formulaSize * 100)}%</div>
                        <input
                            type="range"
                            className="reader-slider"
                            min="0.8"
                            max="1.2"
                            step="0.1"
                            value={formulaSize}
                            onChange={handleFormulaSizeChange}
                        />
                        <div className="reader-settings-hint">80% - 120%</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsPanel;