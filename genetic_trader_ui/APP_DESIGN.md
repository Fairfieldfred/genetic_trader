# Genetic Trader macOS App Design

## Overview

A native macOS application built with Flutter/Dart that provides a graphical interface for configuring, running, and visualizing genetic trading algorithm results.

## App Architecture

### MVVM Pattern
- **Model**: Configuration data, results data
- **View**: Flutter UI screens
- **ViewModel**: Business logic and state management using ChangeNotifier

### Project Structure
```
lib/
├── main.dart                    # App entry point
├── models/
│   ├── config_model.dart       # Configuration data model
│   ├── gene_model.dart         # Gene definition model
│   ├── result_model.dart       # Backtest results model
│   └── trader_model.dart       # Trader/chromosome model
├── viewmodels/
│   ├── config_viewmodel.dart   # Configuration state management
│   ├── evolution_viewmodel.dart # Evolution execution state
│   └── results_viewmodel.dart  # Results state management
├── views/
│   ├── screens/
│   │   ├── home_screen.dart    # Main dashboard
│   │   ├── config_screen.dart  # Configuration editor
│   │   ├── evolution_screen.dart # Evolution execution
│   │   └── results_screen.dart # Results visualization
│   └── widgets/
│       ├── config_widgets.dart # Config UI components
│       ├── charts/             # Chart widgets
│       └── common/             # Reusable components
├── services/
│   ├── python_bridge.dart      # Python process integration
│   ├── config_service.dart     # Config file I/O
│   └── database_service.dart   # SQLite data access
└── utils/
    ├── constants.dart          # App constants
    └── theme.dart              # App theme
```

## Screens

### 1. Home Screen (Dashboard)
**Purpose**: Overview and quick actions

**Features**:
- Recent runs summary
- Quick stats (best fitness, last run date)
- Quick action buttons (New Evolution, View Results, Settings)
- System status (Python available, database connected)

**Layout**:
```
┌─────────────────────────────────────────┐
│  Genetic Trader                    [⚙️] │
├─────────────────────────────────────────┤
│                                         │
│  📊 Recent Runs                         │
│  ┌───────────────────────────────────┐ │
│  │ Run ID: 20250103_120000           │ │
│  │ Return: +16.97%                   │ │
│  │ Trades: 42 (85% win rate)         │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [▶️ Start New Evolution]               │
│  [📈 View Results]                      │
│  [⚙️ Configuration]                     │
│                                         │
└─────────────────────────────────────────┘
```

### 2. Configuration Screen
**Purpose**: Edit config.py parameters

**Sections**:
1. **Portfolio Settings**
   - USE_PORTFOLIO (toggle)
   - PORTFOLIO_SIZE (slider: 1-50)
   - PORTFOLIO_STOCKS (multi-select)
   - INITIAL_ALLOCATION_PCT (slider: 0-100%)

2. **Date Range**
   - TRAIN_START_DATE (date picker)
   - TRAIN_END_DATE (date picker)

3. **Genetic Algorithm**
   - POPULATION_SIZE (number input: 10-100)
   - NUM_GENERATIONS (number input: 10-200)
   - MUTATION_RATE (slider: 0.0-1.0)
   - CROSSOVER_RATE (slider: 0.0-1.0)

4. **Gene Definitions**
   - MA_SHORT_PERIOD (range: min-max)
   - MA_LONG_PERIOD (range: min-max)
   - MA_TYPE (SMA/EMA toggle)
   - STOP_LOSS_PCT (range)
   - TAKE_PROFIT_PCT (range)
   - POSITION_SIZE_PCT (range)

5. **Fitness Weights**
   - total_return (slider with %)
   - sharpe_ratio (slider with %)
   - max_drawdown (slider with %)
   - win_rate (slider with %)
   - Auto-normalize to 100%

**Actions**:
- Save Configuration
- Load Configuration
- Reset to Defaults

**Layout**:
```
┌─────────────────────────────────────────┐
│  Configuration               [Save] [⟲] │
├─────────────────────────────────────────┤
│  📁 Portfolio Settings                  │
│  ┌───────────────────────────────────┐ │
│  │ Portfolio Mode    [✓] ON          │ │
│  │ Portfolio Size    [====●====] 20  │ │
│  │ Initial Alloc     [=========●=] 80% │
│  └───────────────────────────────────┘ │
│                                         │
│  🧬 Genetic Algorithm                   │
│  ┌───────────────────────────────────┐ │
│  │ Population        [  30  ]        │ │
│  │ Generations       [  40  ]        │ │
│  │ Mutation Rate     [====●=] 0.2    │ │
│  └───────────────────────────────────┘ │
│                                         │
│  📊 Fitness Weights (Total: 100%)       │
│  ┌───────────────────────────────────┐ │
│  │ Return      [=========●] 40%      │ │
│  │ Sharpe      [====●====] 24%      │ │
│  │ Drawdown    [====●====] 24%      │ │
│  │ Win Rate    [==●======] 12%      │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 3. Evolution Screen
**Purpose**: Run and monitor evolution process

**Features**:
- Start/Stop/Pause buttons
- Real-time progress (generation counter, % complete)
- Live fitness chart (best, avg, worst per generation)
- Current best trader display
- Estimated time remaining
- Log output (scrolling text)

**Layout**:
```
┌─────────────────────────────────────────┐
│  Evolution Run              [⏸] [⏹]   │
├─────────────────────────────────────────┤
│  Generation: 15/40 (37%)                │
│  [████████░░░░░░░░░░░░]                 │
│                                         │
│  📈 Fitness Progress                    │
│  ┌───────────────────────────────────┐ │
│  │     ^                             │ │
│  │   20│    ╱──────                  │ │
│  │   10│  ╱                          │ │
│  │    0│─                            │ │
│  │     └──────────────────>          │ │
│  │     0    10    20    30    40     │ │
│  └───────────────────────────────────┘ │
│                                         │
│  🏆 Best Trader (Gen 12)                │
│  Fitness: 18.43                         │
│  MA Short: 8, MA Long: 45, Type: EMA   │
│                                         │
│  📋 Log                                 │
│  ┌───────────────────────────────────┐ │
│  │ Gen 15 completed...               │ │
│  │ Best fitness: 18.43               │ │
│  │ Avg fitness: 12.21                │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 4. Results Screen
**Purpose**: View and analyze completed runs

**Features**:
- Run selector (dropdown/list)
- Summary metrics cards
- Fitness evolution chart
- Gene distribution histograms
- Best trader details
- Benchmark comparison
- Export results (JSON, CSV, PDF)

**Layout**:
```
┌─────────────────────────────────────────┐
│  Results                    [Export ▼]  │
├─────────────────────────────────────────┤
│  Run: [20250103_120000        ▼]       │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Return  │ │ Sharpe  │ │Drawdown │  │
│  │ +16.97% │ │  2.34   │ │ -8.5%   │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│                                         │
│  📊 Fitness Evolution                   │
│  [Line chart: generations vs fitness]  │
│                                         │
│  🧬 Best Genes                          │
│  ┌───────────────────────────────────┐ │
│  │ MA Short:  10                     │ │
│  │ MA Long:   50                     │ │
│  │ MA Type:   EMA                    │ │
│  │ Stop Loss: 5.0%                   │ │
│  │ Take Profit: 10.0%                │ │
│  │ Position: 15.0%                   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  📈 vs Buy & Hold: +4.82% ✅            │
└─────────────────────────────────────────┘
```

## Data Flow

### Configuration Flow
```
Config Screen → ConfigViewModel → ConfigService → config.py
                                                    ↓
                                            Python reads config
```

### Evolution Flow
```
Evolution Screen → EvolutionViewModel → PythonBridge → evolve.py
                                                          ↓
                   ← Progress Updates ←  stdout parsing ←
                   ← Results ← summary_{run_id}.json
```

### Results Flow
```
Results Screen → ResultsViewModel → ResultsService → results/*.json
                                                       ↓
                                              Parse and display
```

## Python Integration

### Method 1: Process Bridge (Recommended)
**Pros**: Simple, no dependencies
**Cons**: Need to parse stdout

```dart
// Start Python process
Process.start('python', ['evolve.py'])
  .then((process) {
    process.stdout
      .transform(utf8.decoder)
      .listen((data) {
        // Parse progress updates
      });
  });
```

### Method 2: HTTP API
**Pros**: Clean interface, JSON communication
**Cons**: Requires Flask/FastAPI server

```dart
// Call Python API
http.post('http://localhost:5000/evolve',
  body: jsonEncode(config)
);
```

### Method 3: Platform Channels
**Pros**: Native integration
**Cons**: Complex setup

We'll use **Method 1** (Process Bridge) for simplicity.

## State Management

Using **Provider** pattern with ChangeNotifier:

```dart
class ConfigViewModel extends ChangeNotifier {
  Config _config;

  void updatePortfolioSize(int size) {
    _config.portfolioSize = size;
    notifyListeners();
  }

  Future<void> saveConfig() async {
    await ConfigService.save(_config);
  }
}
```

## Theme

### Color Scheme
- Primary: Deep Purple (#673AB7)
- Secondary: Amber (#FFC107)
- Background: Light Grey (#FAFAFA) / Dark Grey (#121212)
- Success: Green (#4CAF50)
- Error: Red (#F44336)
- Warning: Orange (#FF9800)

### Typography
- Headlines: Roboto Bold
- Body: Roboto Regular
- Code/Numbers: Roboto Mono

### Dark/Light Mode
Support both with system preference detection.

## Charts Library

Use **fl_chart** package for:
- Line charts (fitness evolution)
- Bar charts (gene distributions)
- Pie charts (fitness weight allocation)

## File Structure

### Configuration Files
- `config.py` - Python config (read/write)
- `user_preferences.json` - Flutter app settings

### Data Files
- `spy.db` - SQLite database (read-only from Flutter)
- `results/*.json` - Evolution results
- `results/*.csv` - History files

## Development Phases

### Phase 1: Basic UI ✅
- [x] Create Flutter project
- [ ] Implement home screen
- [ ] Implement config screen
- [ ] Basic navigation

### Phase 2: Python Integration
- [ ] Process bridge implementation
- [ ] Config file read/write
- [ ] Start/stop evolution

### Phase 3: Real-time Monitoring
- [ ] Parse stdout for progress
- [ ] Update UI in real-time
- [ ] Display charts

### Phase 4: Results Visualization
- [ ] Load result files
- [ ] Display metrics
- [ ] Generate charts
- [ ] Export functionality

### Phase 5: Polish
- [ ] Error handling
- [ ] Loading states
- [ ] Animations
- [ ] Testing

## Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  provider: ^6.0.0           # State management
  fl_chart: ^0.65.0         # Charts
  file_picker: ^6.0.0       # File selection
  path_provider: ^2.1.0     # App directories
  sqflite: ^2.3.0          # SQLite database
  http: ^1.1.0             # HTTP requests (if using API)
  intl: ^0.18.0            # Date formatting
```

## Running the App

```bash
cd genetic_trader_ui
flutter run -d macos
```

## Build for Distribution

```bash
flutter build macos --release
```

Output: `build/macos/Build/Products/Release/genetic_trader_ui.app`
