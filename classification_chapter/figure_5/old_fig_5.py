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
                'train_accuracy': 97.58,    # Finale Training Accuracy in %
                'val_accuracy': 98.45,      # Finale Validation Accuracy in %
                'test_accuracy': 98.50,     # Finale Test Accuracy in %
                'train_loss': 0.0368,       # Finale Training Loss
                'val_loss': 0.0339,         # Finale Validation Loss
                'test_loss': 0.0387,        # Finale Test Loss
                'epochs': 13,               # Final model at epoch 13 (early stopping at 18)
                'num_files': 576            # Anzahl Files
            },
            'classification': {
                'train_accuracy': 99.34,    # Finale Training Accuracy in % (epoch 10)
                'val_accuracy': 97.96,      # Finale Validation Accuracy in % (epoch 10)
                'test_accuracy': 97.69,     # Finale Test Accuracy in %
                'train_loss': 0.529,        # Finale Training Loss (epoch 10)
                'val_loss': 0.053,          # Finale Validation Loss (epoch 10)
                'test_loss': 0.07,          # Finale Test Loss (ungefähr)
                'epochs': 10,               # Final model at epoch 10 (early stopping at 15)
                'num_files': 576            # Anzahl Files (gleich für einen Vogel)
            }
        },
        'Bird 2': {
            'internal_name': 'Br08pk08',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 96.00,    # Finale Training Accuracy in % (epoch 15)
                'val_accuracy': 95.47,      # Finale Validation Accuracy in % (epoch 15)
                'test_accuracy': 95.75,    # Finale Test Accuracy in % (epoch 15)
                'train_loss': 0.1054,       # Finale Training Loss (epoch 15)
                'val_loss': 0.1243,         # Finale Validation Loss (epoch 15)
                'test_loss': 0.1107,        # Finale Test Loss (epoch 15)
                'epochs': 15,               # Final model at epoch 15 (early stopping at 15)
                'num_files': 194            # Anzahl Files (aus batch.txt Dateien gezählt)
            },
            'classification': {
                'train_accuracy': 98.96,    # Finale Training Accuracy in % (epoch 11)
                'val_accuracy': 93.97,      # Finale Validation Accuracy in % (epoch 11)
                'test_accuracy': 94.49,     # Finale Test Accuracy in %
                'train_loss': 0.0850,       # Finale Training Loss (epoch 11)
                'val_loss': 0.2281,         # Finale Validation Loss (epoch 11)
                'test_loss': 0.2565,        # Finale Test Loss
                'epochs': 11,               # Final model at epoch 11 (early stopping at 16)
                'num_files': 194            # Anzahl Files (gleich wie segmentation)
            }
        },
        'Bird 3': {
            'internal_name': 'bu0bk04_2',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 94.93,     # Finale Training Accuracy in % (epoch 18)
                'val_accuracy': 95.26,      # Finale Validation Accuracy in % (epoch 18)
                'test_accuracy': 94.37,     # Finale Test Accuracy in %
                'train_loss': 0.1344,       # Finale Training Loss (epoch 18)
                'val_loss': 0.1212,         # Finale Validation Loss (epoch 18)
                'test_loss': 0.1517,        # Finale Test Loss
                'epochs': 18,               # Final model at epoch 18 (early stopping at 23)
                'num_files': 172            # Anzahl Files (aus batch.txt Dateien gezählt)
            },
            'classification': {
                'train_accuracy': 97.83,    # Finale Training Accuracy in % (epoch 12)
                'val_accuracy': 92.89,      # Finale Validation Accuracy in % (epoch 12)
                'test_accuracy': 95.32,     # Finale Test Accuracy in %
                'train_loss': 0.1279,       # Finale Training Loss (epoch 12)
                'val_loss': 0.2100,         # Finale Validation Loss (epoch 12)
                'test_loss': 0.1645,        # Finale Test Loss
                'epochs': 12,               # Final model at epoch 12 (early stopping at 20)
                'num_files': 172            # Anzahl Files (gleich wie segmentation)
            }
        },
        'Bird 4': {
            'internal_name': 'Gy07bu07_3',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 96.27,    # Finale Training Accuracy in % (epoch 14)
                'val_accuracy': 96.15,      # Finale Validation Accuracy in % (epoch 14)
                'test_accuracy': 96.07,     # Finale Test Accuracy in % (epoch 14)
                'train_loss': 0.0923,       # Finale Training Loss (epoch 14)
                'val_loss': 0.0963,         # Finale Validation Loss (epoch 14)
                'test_loss': 0.1003,        # Finale Test Loss (epoch 14)
                'epochs': 14,               # Final model at epoch 14 (early stopping at 14)
                'num_files': 112            # Anzahl Files (aus batch.txt Dateien gezählt)
            },
            'classification': {
                'train_accuracy': 99.84,    # Finale Training Accuracy in % (epoch 15)
                'val_accuracy': 98.08,      # Finale Validation Accuracy in % (epoch 15)
                'test_accuracy': 98.45,     # Finale Test Accuracy in %
                'train_loss': 0.0113,       # Finale Training Loss (epoch 15)
                'val_loss': 0.0648,         # Finale Validation Loss (epoch 15)
                'test_loss': 0.0488,        # Finale Test Loss
                'epochs': 15,               # Final model at epoch 15 (early stopping at 20)
                'num_files': 112            # Anzahl Files (gleich wie segmentation)
            }
        },
        'Bird 5': {
            'internal_name': 'Ye04gr05_4',  # Internal name from training logs
            'segmentation': {
                'train_accuracy': 97.25,    # Finale Training Accuracy in % (epoch 17)
                'val_accuracy': 96.96,      # Finale Validation Accuracy in % (epoch 17)
                'test_accuracy': 97.55,      # Finale Test Accuracy in % (epoch 17)
                'train_loss': 0.0707,       # Finale Training Loss (epoch 17)
                'val_loss': 0.0795,         # Finale Validation Loss (epoch 17)
                'test_loss': 0.0679,        # Finale Test Loss (epoch 17)
                'epochs': 17,               # Final model at epoch 17 (early stopping at 17)
                'num_files': 39            # Anzahl Files (aus batch.txt Dateien gezählt)
            },
            'classification': {
                'train_accuracy': 97.33,    # Finale Training Accuracy in % (epoch 10)
                'val_accuracy': 92.24,      # Finale Validation Accuracy in % (epoch 10)
                'test_accuracy': 91.30,     # Finale Test Accuracy in %
                'train_loss': 0.1398,       # Finale Training Loss (epoch 10)
                'val_loss': 0.2656,         # Finale Validation Loss (epoch 10)
                'test_loss': 0.3358,        # Finale Test Loss
                'epochs': 10,               # Final model at epoch 10 (early stopping at 16)
                'num_files': 39            # Anzahl Files (gleich wie segmentation)
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

# Funktion zum Erstellen der finalen Plots mit Test-Daten (nur Classification)
def plot_final_4panels(bird_data, test_data, output_path, colors):
    """
    Erstellt die finalen 2-Panel Plots mit Test-Daten als Dots (nur Classification: Accuracy & Loss).
    """
    from matplotlib import font_manager
    regular_font_prop = font_manager.FontProperties(fname='/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf')
    bold_font_prop = font_manager.FontProperties(fname='/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf')

    # Erstelle Figur mit 2 Subplots (1x2 Layout)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(STANDARD_PLOT_WIDTH, 4))
    
    # Farben und Linienstile für verschiedene Vögel
    bird_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    line_styles = ['-', '--', '-.', ':', '-']  # Durchgezogen, Gestrichelt, Strich-Punkt, Punkte, Durchgezogen
    
    # Vogel-Namen in der gewünschten Reihenfolge
    bird_names = ['Bird 1', 'Bird 2', 'Bird 3', 'Bird 4', 'Bird 5']
    x_pos = np.arange(len(bird_names))
    
    # Sammle Daten für alle Vögel (nur Classification)
    class_train_acc = []
    class_val_acc = []
    class_test_acc = []
    class_train_loss = []
    class_val_loss = []
    class_test_loss = []
    
    for bird_name in bird_names:
        # Classification Daten
        if bird_name in bird_data and 'classification' in bird_data[bird_name]:
            class_data = bird_data[bird_name]['classification']
            class_train_acc.append(class_data['train_accuracy'])      # Finale Training-Daten
            class_val_acc.append(class_data['val_accuracy'])          # Finale Validation-Daten
            class_train_loss.append(class_data['train_loss'])         # Finale Training-Daten
            class_val_loss.append(class_data['val_loss'])             # Finale Validation-Daten
            # Test-Daten direkt aus bird_data lesen
            if 'test_accuracy' in class_data:
                class_test_acc.append(class_data['test_accuracy'])    # Finale Test-Daten
            else:
                class_test_acc.append(0)
            if 'test_loss' in class_data:
                class_test_loss.append(class_data['test_loss'])       # Finale Test-Daten
            else:
                class_test_loss.append(0)
        else:
            class_train_acc.append(0)
            class_val_acc.append(0)
            class_train_loss.append(0)
            class_val_loss.append(0)
            class_test_acc.append(0)
            class_test_loss.append(0)
    
    # Plotte alle Vögel als Dots mit verschiedenen Linienstilen
    for i, bird_name in enumerate(bird_names):
        color = bird_colors[i % len(bird_colors)]
        line_style = line_styles[i % len(line_styles)]
        
        # Panel A: Classification Accuracy
        # Training und Validation transparenter
        ax1.plot(x_pos[i], class_train_acc[i], 'o', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Training' if i == 0 else "")
        ax1.plot(x_pos[i], class_val_acc[i], 's', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Validation' if i == 0 else "")
        # Test: gleiche Größe aber fett (markeredgewidth)
        ax1.plot(x_pos[i], class_test_acc[i], '^', color=color, markersize=8, 
                linestyle='None', alpha=1.0, markeredgewidth=2.5, label=f'{bird_name} Test' if i == 0 else "")
        
        # Panel B: Classification Loss
        # Training und Validation transparenter
        ax2.plot(x_pos[i], class_train_loss[i], 'o', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Training' if i == 0 else "")
        ax2.plot(x_pos[i], class_val_loss[i], 's', color=color, markersize=8, 
                linestyle='None', alpha=0.4, markeredgewidth=1, label=f'{bird_name} Validation' if i == 0 else "")
        # Test: gleiche Größe aber fett (markeredgewidth)
        ax2.plot(x_pos[i], class_test_loss[i], '^', color=color, markersize=8, 
                linestyle='None', alpha=1.0, markeredgewidth=2.5, label=f'{bird_name} Test' if i == 0 else "")
    
    # Erstelle X-Achsen-Labels für Classification
    class_labels = []
    
    for i, bird_name in enumerate(bird_names):
        # Sammle Datei-Anzahlen und Epochs direkt aus bird_data
        class_files = 'X'
        class_epochs = 'X'
        
        if bird_name in bird_data and 'classification' in bird_data[bird_name]:
            class_data = bird_data[bird_name]['classification']
            class_epochs = class_data.get('epochs', 'X')
            class_files = class_data.get('num_files', 'X')
        
        # Erstelle Labels mit n=... Format
        class_label = f'{bird_name}\nn={class_files}\ne={class_epochs}'
        
        class_labels.append(class_label)
    
    # Panel A: Classification Accuracy
    ax1.set_xlabel('', fontproperties=regular_font_prop)
    ax1.set_ylabel('Accuracy', fontproperties=regular_font_prop)
    ax1.set_title('Classification Network Accuracy', fontproperties=bold_font_prop)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(class_labels, rotation=0, ha='center', fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0%}'))
    
    # Panel B: Classification Loss
    ax2.set_xlabel('', fontproperties=regular_font_prop)
    ax2.set_ylabel('Loss', fontproperties=regular_font_prop)
    ax2.set_title('Classification Network Loss', fontproperties=bold_font_prop)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(class_labels, rotation=0, ha='center', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # Y-Label Positionen anpassen
    labelx = -0.12
    for ax in (ax1, ax2):
        ax.yaxis.set_label_coords(labelx, 0.5)
    
    # Erweiterte Legende mit Data Types und Erklärungen
    from matplotlib.lines import Line2D
    
    marker_elements = [
        Line2D([0], [0], marker='o', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=1, label='Training'),
        Line2D([0], [0], marker='s', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=1, label='Validation'),
        Line2D([0], [0], marker='^', color='black', linestyle='None', markersize=8, alpha=1.0, markeredgewidth=2.5, label='Test'),
        Line2D([0], [0], marker='', color='none', linestyle='None', label='n = files, e = epochs')  # Text ohne Marker
    ]
    
    # Erstelle erweiterte Legende mit Erklärungen
    legend = fig.legend(handles=marker_elements, loc='lower center', bbox_to_anchor=(0.5, -0.08), 
              ncol=4, frameon=True, fontsize=9, title='Data Types', 
              title_fontproperties=bold_font_prop)
    
    # Layout anpassen
    plt.tight_layout()
    plt.subplots_adjust(right=0.95, left=0.12, bottom=0.20)  # Platz für Legende
    
    # Subplot-Labels (A, B)
    ax1.text(labelx, 1.15, 'A', transform=ax1.transAxes, fontsize=14, fontproperties=bold_font_prop, va='top')
    ax2.text(labelx, 1.15, 'B', transform=ax2.transAxes, fontsize=14, fontproperties=bold_font_prop, va='top')
    
    # Speichere Plot
    save_plot_for_word(fig, os.path.join(output_path, 'figure5_classification_A_B.png'))
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
    print("   - figure5_classification_A_B.png (Classification: Accuracy & Loss mit Test-Daten)")

if __name__ == '__main__':
    generate_final_plots()
