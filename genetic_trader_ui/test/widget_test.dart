// Widget test for GeneticTraderApp
// Uses a large test surface (1920x1080) to avoid layout overflow
// in the responsive split-panel UI.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:genetic_trader_ui/main.dart';

void main() {
  testWidgets('App initializes without errors', (WidgetTester tester) async {
    // Use a desktop-sized surface so the split-panel layout has room to render.
    tester.view.physicalSize = const Size(1920, 1080);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const GeneticTraderApp());
    await tester.pump();

    // Verify the app builds successfully.
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
