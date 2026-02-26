import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'views/screens/home_screen.dart';
import 'viewmodels/config_viewmodel.dart';
import 'utils/theme.dart';

void main() {
  runApp(const GeneticTraderApp());
}

class GeneticTraderApp extends StatelessWidget {
  const GeneticTraderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ConfigViewModel()),
      ],
      child: MaterialApp(
        title: 'Genetic Trader',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        home: const HomeScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
