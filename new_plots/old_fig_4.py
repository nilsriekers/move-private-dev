import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties
import pandas as pd

# Function to create the output directory if it doesn't exist
def create_output_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Function to set global Matplotlib style parameters
def set_matplotlib_style():
    latex_font_path = '/Library/Fonts/CMU-Serif-Roman/'
    regular_font_path = os.path.join(latex_font_path, 'cmunrm.ttf')
    bold_font_path = os.path.join(latex_font_path, 'cmunbx.ttf')

    font_files = [regular_font_path, bold_font_path]
    from matplotlib import font_manager
    for font_file in font_files:
        font_manager.fontManager.addfont(font_file)

    # Konsistente Schriftgrößen für alle Plots
    rcParams['font.family'] = 'CMU Serif'
    rcParams['font.size'] = 12
    rcParams['axes.labelsize'] = 12
    rcParams['axes.titlesize'] = 14
    rcParams['legend.fontsize'] = 10
    rcParams['xtick.labelsize'] = 11
    rcParams['ytick.labelsize'] = 11
    rcParams['figure.dpi'] = 300
    rcParams['savefig.dpi'] = 300
    rcParams['text.usetex'] = False
    rcParams['font.weight'] = 'normal'
    
    # Konsistente Linien- und Marker-Eigenschaften
    rcParams['lines.linewidth'] = 2
    rcParams['lines.markersize'] = 8
    rcParams['grid.alpha'] = 0.3
    rcParams['grid.linewidth'] = 0.5
    
    # Konsistente Achsen-Eigenschaften
    rcParams['axes.linewidth'] = 0.8
    rcParams['axes.spines.top'] = False
    rcParams['axes.spines.right'] = False
    rcParams['axes.grid'] = True
    rcParams['axes.axisbelow'] = True

# Funktion zum Erstellen von einfachen Vogel-Daten
def create_simple_bird_data():
    """
    Einfache Datenstruktur - nur finale Werte eingeben!
    Format: 'train_accuracy': 97.58 (als Prozent), 'epochs': 18, etc.
    """
    print("📁 Erstelle einfache Vogel-Daten...")
    
    # HIER KANNST DU EINFACH DIE FINALEN WERTE EINGEBEN:
    bird_data = {
        'Bird 1': {
            'internal_name': 'ye00pu07',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 97.58,    # Finale Training Accuracy in % (epoch 13)
                'val_accuracy': 98.45,      # Finale Validation Accuracy in % (epoch 13)
                'test_accuracy': 98.50,     # Finale Test Accuracy in %
                'train_loss': 0.0368,       # Finale Training Loss (epoch 13)
                'val_loss': 0.0339,         # Finale Validation Loss (epoch 13)
                'test_loss': 0.0387,        # Finale Test Loss
                'epochs': 18,               # Total epochs (early stopping at 18)
                'best_epoch': 13,           # Best model at epoch 13
                'num_files': 576            # Anzahl Files
            },
            'classification': {
                'train_accuracy': 99.34,    # Finale Training Accuracy in % (epoch 10)
                'val_accuracy': 97.96,      # Finale Validation Accuracy in % (epoch 10)
                'test_accuracy': 97.69,     # Finale Test Accuracy in %
                'train_loss': 0.0529,       # Finale Training Loss (epoch 10)
                'val_loss': 0.0530,         # Finale Validation Loss (epoch 10)
                'test_loss': 0.0700,        # Finale Test Loss
                'epochs': 15,               # Total epochs (early stopping at 15)
                'best_epoch': 10,           # Best model at epoch 10
                'num_syllables': 576,       # Anzahl Syllables
                'num_classes': 9            # Anzahl Klassen (c/h merged)
            }
        },
        'Bird 2': {
            'internal_name': 'Ye04gr05',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 94.92,    # Finale Training Accuracy in % (epoch 13)
                'val_accuracy': 95.24,      # Finale Validation Accuracy in % (epoch 13)
                'test_accuracy': 94.30,     # Finale Test Accuracy in %
                'train_loss': 0.1323,       # Finale Training Loss (epoch 13)
                'val_loss': 0.1213,         # Finale Validation Loss (epoch 13)
                'test_loss': 0.1450,        # Finale Test Loss
                'epochs': 18,               # Total epochs (early stopping at 18)
                'best_epoch': 13,           # Best model at epoch 13
                'num_files': 108            # Anzahl Files (total bouts)
            },
            'classification': {
                'train_accuracy': 98.03,    # Finale Training Accuracy in % (epoch 9)
                'val_accuracy': 96.43,      # Finale Validation Accuracy in % (epoch 9)
                'test_accuracy': 97.84,     # Finale Test Accuracy in %
                'train_loss': 0.0778,       # Finale Training Loss (epoch 9)
                'val_loss': 0.1389,         # Finale Validation Loss (epoch 9)
                'test_loss': 0.1263,        # Finale Test Loss
                'epochs': 14,               # Total epochs (early stopping at 14)
                'best_epoch': 9,            # Best model at epoch 9
                'num_syllables': 108,       # Anzahl Syllables (total bouts)
                'num_classes': 8            # Anzahl Klassen
            }
        },
        'Bird 3': {
            'internal_name': 'Gy07bu07',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 96.09,    # Finale Training Accuracy in % (epoch 9)
                'val_accuracy': 96.35,      # Finale Validation Accuracy in % (epoch 9)
                'test_accuracy': 96.26,     # Finale Test Accuracy in %
                'train_loss': 0.0982,       # Finale Training Loss (epoch 9)
                'val_loss': 0.0926,         # Finale Validation Loss (epoch 9)
                'test_loss': 0.0974,        # Finale Test Loss
                'epochs': 14,               # Total epochs (early stopping at 14)
                'best_epoch': 9,            # Best model at epoch 9
                'num_files': 113            # Anzahl Files (total bouts)
            },
            'classification': {
                'train_accuracy': 99.51,    # Finale Training Accuracy in % (epoch 12)
                'val_accuracy': 98.85,      # Finale Validation Accuracy in % (epoch 12)
                'test_accuracy': 97.77,     # Finale Test Accuracy in %
                'train_loss': 0.0261,       # Finale Training Loss (epoch 12)
                'val_loss': 0.0356,         # Finale Validation Loss (epoch 12)
                'test_loss': 0.0808,        # Finale Test Loss
                'epochs': 17,               # Total epochs (early stopping at 17)
                'best_epoch': 12,           # Best model at epoch 12
                'num_syllables': 113,       # Anzahl Syllables (total bouts)
                'num_classes': 8            # Anzahl Klassen
            }
        },
        'Bird 4': {
            'internal_name': 'Bu04bk04',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 95.08,    # Finale Training Accuracy in % (epoch 19)
                'val_accuracy': 95.32,      # Finale Validation Accuracy in % (epoch 19)
                'test_accuracy': 94.46,     # Finale Test Accuracy in %
                'train_loss': 0.1299,       # Finale Training Loss (epoch 19)
                'val_loss': 0.1210,         # Finale Validation Loss (epoch 19)
                'test_loss': 0.1467,        # Finale Test Loss
                'epochs': 24,               # Total epochs (early stopping at 24)
                'best_epoch': 19,           # Best model at epoch 19
                'num_files': 176            # Anzahl Files (total bouts)
            },
            'classification': {
                'train_accuracy': 98.71,    # Finale Training Accuracy in % (epoch 5)
                'val_accuracy': 96.63,      # Finale Validation Accuracy in % (epoch 5)
                'test_accuracy': 96.12,     # Finale Test Accuracy in %
                'train_loss': 0.0968,       # Finale Training Loss (epoch 5)
                'val_loss': 0.1135,         # Finale Validation Loss (epoch 5)
                'test_loss': 0.2057,        # Finale Test Loss
                'epochs': 10,               # Total epochs (early stopping at 10)
                'best_epoch': 5,            # Best model at epoch 5
                'num_syllables': 176,       # Anzahl Syllables (total bouts)
                'num_classes': 10           # Anzahl Klassen
            }
        },
        'Bird 5': {
            'internal_name': 'Br08pk08',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 95.84,    # Finale Training Accuracy in % (epoch 7)
                'val_accuracy': 95.79,      # Finale Validation Accuracy in % (epoch 7)
                'test_accuracy': 96.04,     # Finale Test Accuracy in %
                'train_loss': 0.1115,       # Finale Training Loss (epoch 7)
                'val_loss': 0.1150,         # Finale Validation Loss (epoch 7)
                'test_loss': 0.1048,        # Finale Test Loss
                'epochs': 12,               # Total epochs (early stopping at 12)
                'best_epoch': 7,            # Best model at epoch 7
                'num_files': 199            # Anzahl Files (total bouts)
            },
            'classification': {
                'train_accuracy': 98.63,    # Finale Training Accuracy in % (epoch 10)
                'val_accuracy': 94.33,      # Finale Validation Accuracy in % (epoch 10)
                'test_accuracy': 96.45,     # Finale Test Accuracy in %
                'train_loss': 0.0933,       # Finale Training Loss (epoch 10)
                'val_loss': 0.2392,         # Finale Validation Loss (epoch 10)
                'test_loss': 0.1441,        # Finale Test Loss
                'epochs': 15,               # Total epochs (early stopping at 15)
                'best_epoch': 10,           # Best model at epoch 10
                'num_syllables': 199,       # Anzahl Syllables (total bouts)
                'num_classes': 8            # Anzahl Klassen
            }
        }
    }
    
    # Konvertiere Prozent-Werte zu Dezimal-Werten für die Plots
    for bird_name in bird_data:
        for network_type in ['segmentation', 'classification']:
            if network_type in bird_data[bird_name]:
                # Konvertiere Prozent zu Dezimal (97.58 -> 0.9758)
                bird_data[bird_name][network_type]['train_accuracy'] = bird_data[bird_name][network_type]['train_accuracy'] / 100.0
                bird_data[bird_name][network_type]['val_accuracy'] = bird_data[bird_name][network_type]['val_accuracy'] / 100.0
                # Konvertiere Test-Accuracy falls vorhanden
                if 'test_accuracy' in bird_data[bird_name][network_type]:
                    bird_data[bird_name][network_type]['test_accuracy'] = bird_data[bird_name][network_type]['test_accuracy'] / 100.0
    
    print(f"✅ Einfache Daten für {len(bird_data)} Vögel erstellt")
    print(f"📊 Vögel: {list(bird_data.keys())}")
    
    return bird_data

# Hinweis: Die ursprünglichen Funktionen organize_bird_data() und load_old_npy_data() 
# wurden entfernt, da jetzt Dummy-Daten verwendet werden.

# Test-Daten und Datei-Anzahlen (Dummy-Werte)
def get_dummy_test_data_and_file_counts():
    """
    Gibt Dummy-Test-Daten und Datei-Anzahlen für alle Vögel zurück.
    Diese können manuell angepasst werden.
    """
    return {
        'Bird 1': {
            'segmentation': {'test_accuracy': 0.9850, 'test_loss': 0.0387, 'num_files': 576},
            'classification': {'test_accuracy': 'xx', 'test_loss': 'xx', 'num_files': 576}  # Keine Test-Daten im Text erwähnt
        },
        'Bird 2': {
            'segmentation': {'test_accuracy': 0.9575, 'test_loss': 0.1107, 'num_files': 100},
            'classification': {'test_accuracy': 'xx', 'test_loss': 'xx', 'num_files': 100}
        },
        'Bird 3': {
            'segmentation': {'test_accuracy': 0.9443, 'test_loss': 0.1495, 'num_files': 200},
            'classification': {'test_accuracy': 'xx', 'test_loss': 'xx', 'num_files': 200}
        },
        'Bird 4': {
            'segmentation': {'test_accuracy': 0.9607, 'test_loss': 0.1003, 'num_files': 400},
            'classification': {'test_accuracy': 'xx', 'test_loss': 'xx', 'num_files': 400}
        },
        'Bird 5': {
            'segmentation': {'test_accuracy': 0.9755, 'test_loss': 0.0679, 'num_files': 500},
            'classification': {'test_accuracy': 'xx', 'test_loss': 'xx', 'num_files': 500}
        }
    }

# Funktion für Word-kompatible Plot-Speicherung
def save_plot_for_word(fig, output_path, target_size=(6, 4), dpi=300):
    """
    Speichert einen Plot in konsistenter Größe für Word-Kompatibilität.
    """
    plt.savefig(output_path, 
                format='png',
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none')
    plt.close()

# Standard-Breite für alle Plots (Word-kompatibel)
STANDARD_PLOT_WIDTH = 12  # 12 Zoll Breite für alle Plots

# Funktion zum Erstellen der finalen Plots mit Test-Daten (nur Segmentation)
def plot_final_4panels(bird_data, test_data, output_path, colors):
    """
    Erstellt die finalen 2-Panel Plots mit Test-Daten als Dots (nur Segmentation: Accuracy & Loss).
    """
    from matplotlib import font_manager
    regular_font_prop = font_manager.FontProperties(fname='/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf')
    bold_font_prop = font_manager.FontProperties(fname='/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf')

    # Erstelle Figur mit 2 Subplots (1x2 Layout)
    # Höhe angepasst für Konsistenz mit 6-panel Figure (12x12 mit 3 Reihen = 4 pro Reihe)
    # Aber mit gleichen Proportionen wie eine Reihe im 6-panel
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(STANDARD_PLOT_WIDTH, 3.5))
    
    # Farben und Linienstile für verschiedene Vögel
    bird_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    line_styles = ['-', '--', '-.', ':', '-']  # Durchgezogen, Gestrichelt, Strich-Punkt, Punkte, Durchgezogen
    
    # Vogel-Namen in der gewünschten Reihenfolge
    bird_names = ['Bird 1', 'Bird 2', 'Bird 3', 'Bird 4', 'Bird 5']
    x_pos = np.arange(len(bird_names))
    
    # Sammle Daten für alle Vögel (nur Segmentation)
    seg_train_acc = []
    seg_val_acc = []
    seg_test_acc = []
    seg_train_loss = []
    seg_val_loss = []
    seg_test_loss = []
    
    for bird_name in bird_names:
        # Segmentation Daten
        if bird_name in bird_data and 'segmentation' in bird_data[bird_name]:
            seg_data = bird_data[bird_name]['segmentation']
            seg_train_acc.append(seg_data['train_accuracy'])      # Finale Training-Daten
            seg_val_acc.append(seg_data['val_accuracy'])          # Finale Validation-Daten
            seg_train_loss.append(seg_data['train_loss'])         # Finale Training-Daten
            seg_val_loss.append(seg_data['val_loss'])             # Finale Validation-Daten
            # Test-Daten direkt aus bird_data lesen
            if 'test_accuracy' in seg_data:
                seg_test_acc.append(seg_data['test_accuracy'])    # Finale Test-Daten
            else:
                seg_test_acc.append(0)
            if 'test_loss' in seg_data:
                seg_test_loss.append(seg_data['test_loss'])       # Finale Test-Daten
            else:
                seg_test_loss.append(0)
        else:
            seg_train_acc.append(0)
            seg_val_acc.append(0)
            seg_train_loss.append(0)
            seg_val_loss.append(0)
            seg_test_acc.append(0)
            seg_test_loss.append(0)
    
    # Plotte alle Vögel als Dots mit verschiedenen Linienstilen
    for i, bird_name in enumerate(bird_names):
        color = bird_colors[i % len(bird_colors)]
        line_style = line_styles[i % len(line_styles)]
        
        # Panel A: Segmentation Accuracy
        # Training und Validation transparenter
        ax1.plot(x_pos[i], seg_train_acc[i], 'o', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Training' if i == 0 else "")
        ax1.plot(x_pos[i], seg_val_acc[i], 's', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Validation' if i == 0 else "")
        # Test: gleiche Größe aber fett (markeredgewidth)
        ax1.plot(x_pos[i], seg_test_acc[i], '^', color=color, markersize=8, 
                linestyle='None', alpha=1.0, markeredgewidth=2.5, label=f'{bird_name} Test' if i == 0 else "")
        
        # Panel B: Segmentation Loss
        # Training und Validation transparenter
        ax2.plot(x_pos[i], seg_train_loss[i], 'o', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Training' if i == 0 else "")
        ax2.plot(x_pos[i], seg_val_loss[i], 's', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Validation' if i == 0 else "")
        # Test: gleiche Größe aber fett (markeredgewidth)
        ax2.plot(x_pos[i], seg_test_loss[i], '^', color=color, markersize=8, 
                linestyle='None', alpha=1.0, markeredgewidth=2.5, label=f'{bird_name} Test' if i == 0 else "")
    
    # Erstelle X-Achsen-Labels für Segmentation (nur Vogel-Namen, ohne n/e)
    seg_labels = []
    
    # Sammle Datei-Anzahlen und Epochs für die Ausgabe
    seg_files_list = []
    seg_epochs_list = []
    
    for i, bird_name in enumerate(bird_names):
        # Nur Vogel-Namen in X-Achsen-Labels
        seg_labels.append(bird_name)
        
        # Sammle Datei-Anzahlen und Epochs
        seg_files = 'X'
        seg_epochs = 'X'
        
        if bird_name in bird_data and 'segmentation' in bird_data[bird_name]:
            seg_data = bird_data[bird_name]['segmentation']
            seg_epochs = seg_data.get('epochs', 'X')
            seg_files = seg_data.get('num_files', 'X')
        
        seg_files_list.append(seg_files)
        seg_epochs_list.append(seg_epochs)
    
    # Drucke die Angaben
    print("\n📊 Datei-Anzahlen und Epochs:")
    for i, bird_name in enumerate(bird_names):
        print(f"   {bird_name}: n={seg_files_list[i]}, e={seg_epochs_list[i]}")
    
    # Panel A: Segmentation Accuracy
    ax1.set_xlabel('', fontproperties=regular_font_prop)
    ax1.set_ylabel('Accuracy', fontproperties=regular_font_prop)
    ax1.set_title('Segmentation Network Accuracy', fontproperties=bold_font_prop)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(seg_labels, rotation=0, ha='center', fontsize=11)
    ax1.set_ylim(bottom=0.5, top=1.0)  # Von 50% bis 100%
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0%}'))
    
    # Panel B: Segmentation Loss
    ax2.set_xlabel('', fontproperties=regular_font_prop)
    ax2.set_ylabel('Loss', fontproperties=regular_font_prop)
    ax2.set_title('Segmentation Network Loss', fontproperties=bold_font_prop)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(seg_labels, rotation=0, ha='center', fontsize=11)
    ax2.set_ylim(bottom=0)
    ax2.grid(True, alpha=0.3)
    
    # Y-Label Positionen anpassen
    labelx = -0.12
    for ax in (ax1, ax2):
        ax.yaxis.set_label_coords(labelx, 0.5)
    
    # Legende mit Data Types und Erklärungen
    from matplotlib.lines import Line2D
    
    marker_elements = [
        Line2D([0], [0], marker='o', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=1, label='Training'),
        Line2D([0], [0], marker='s', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=1, label='Validation'),
        Line2D([0], [0], marker='^', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=2.5, label='Test'),
    ]
    
    # Layout anpassen - gleiche Proportionen wie im 6-panel Figure
    # KEIN tight_layout für Konsistenz
    plt.subplots_adjust(right=0.95, left=0.12, bottom=0.18, top=0.88, wspace=0.3)
    
    # Legende in Plot A positionieren (wie in create_combined_6panels_figure_rearranged.py)
    pos1 = ax1.get_position()
    legend_x = (pos1.x0 + pos1.x1) / 2  # Zentriert unter Plot A
    # === PARAMETER: Höhe der Data Types Legende ===
    legend_y_offset = 0.09  # Erhöhen = weiter nach oben
    legend_y = pos1.y0 + legend_y_offset  # Im Plot, über der x-Achse
    
    legend = fig.legend(handles=marker_elements, loc='center', bbox_to_anchor=(legend_x, legend_y), 
              ncol=3, frameon=True, fontsize=12, columnspacing=1.2, handletextpad=0.5, 
              borderpad=0.4, handlelength=1.2, title='Data Types:',
              title_fontproperties=bold_font_prop)
    
    # === ZENTRALER PARAMETER: Titel-Höhe für alle Plots ===
    TITLE_PAD = 10  # Abstand des Titels vom Plot (in Punkten)
    for ax in [ax1, ax2]:
        if ax.get_title():
            ax.set_title(ax.get_title(), pad=TITLE_PAD)
    
    # === PARAMETER: Plot A und B Breite ===
    PLOT_A_WIDTH_SCALE = 0.9  # 1.0 = volle Breite, 0.8 = 80% Breite, etc.
    PLOT_B_WIDTH_SCALE = 0.9  # 1.0 = volle Breite, 0.8 = 80% Breite, etc.
    
    # Speichere originale Positionen von A und B
    pos1_original = ax1.get_position()
    pos2_original = ax2.get_position()
    
    # Plot A anpassen wenn gewünscht
    if PLOT_A_WIDTH_SCALE != 1.0:
        new_width_a = pos1_original.width * PLOT_A_WIDTH_SCALE
        center_x_a = (pos1_original.x0 + pos1_original.x1) / 2
        new_x0_a = center_x_a - new_width_a / 2
        ax1.set_position([new_x0_a, pos1_original.y0, new_width_a, pos1_original.height])
    
    # Plot B anpassen wenn gewünscht
    if PLOT_B_WIDTH_SCALE != 1.0:
        new_width_b = pos2_original.width * PLOT_B_WIDTH_SCALE
        center_x_b = (pos2_original.x0 + pos2_original.x1) / 2
        new_x0_b = center_x_b - new_width_b / 2
        ax2.set_position([new_x0_b, pos2_original.y0, new_width_b, pos2_original.height])
    
    # === PARAMETER: Label-Position ===
    label_y_offset = 1.2  # Relative Höhe über dem Plot (in Einheiten der Plot-Höhe)
    
    # Subplot-Labels (A, B) - basierend auf originalen Positionen
    a_label_x = pos1_original.x0 + labelx * pos1_original.width
    a_label_y = pos1_original.y0 + label_y_offset * pos1_original.height
    b_label_x = pos2_original.x0 + labelx * pos2_original.width
    b_label_y = pos2_original.y0 + label_y_offset * pos2_original.height
    
    fig.text(a_label_x, a_label_y, 'A', fontsize=20, fontproperties=bold_font_prop, va='top', ha='left')
    fig.text(b_label_x, b_label_y, 'B', fontsize=20, fontproperties=bold_font_prop, va='top', ha='left')
    
    # Speichere Plot
    save_plot_for_word(fig, os.path.join(output_path, 'figure4_segmentation_only.png'))
    print(f"✅ Final Plot gespeichert: {len(bird_data)} Vögel")


# Main function
def generate_final_plots():
    """
    Hauptfunktion zum Generieren der finalen Plots.
    """
    set_matplotlib_style()
    
    # Farben definieren
    colors = {
        'train': '#1f77b4',  # Blue
        'val': '#ff7f0e',    # Orange
    }
    
    # Einfache Daten erstellen (kann manuell angepasst werden)
    all_bird_data = create_simple_bird_data()
    
    # Dummy-Test-Daten laden (kann manuell angepasst werden)
    test_data = get_dummy_test_data_and_file_counts()
    
    print(f"\n📊 Gesamt: {len(all_bird_data)} Vögel")
    print(f"   - Dummy-Vögel: {list(all_bird_data.keys())}")
    
    # Output-Verzeichnis erstellen
    output_dir = '/Users/riekers/git/nirsonganaly_dev/final_plots'
    create_output_dir(output_dir)
    
    # Finale Plots erstellen
    print("\n🎨 Erstelle finale Plots...")
    
    # Hauptplot mit Test-Daten und zentraler Legende
    plot_final_4panels(all_bird_data, test_data, output_dir, colors)
    
    print(f"\n🎉 Alle finalen Plots erstellt in: {output_dir}")
    print("📁 Verfügbare Plots:")
    print("   - figure4_segmentation_only.png (Segmentation: Accuracy & Loss mit Test-Daten)")

if __name__ == '__main__':
    generate_final_plots()
