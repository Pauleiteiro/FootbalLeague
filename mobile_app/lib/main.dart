import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const TercasFCApp());
}

class TercasFCApp extends StatelessWidget {
  const TercasFCApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Terças FC',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.green,
        scaffoldBackgroundColor: const Color(0xFF121212), // Fundo escuro bonito
        colorScheme: const ColorScheme.dark(
          primary: Colors.green,
          secondary: Colors.greenAccent,
        ),
      ),
      home: const LeaderboardPage(),
    );
  }
}

class LeaderboardPage extends StatefulWidget {
  const LeaderboardPage({super.key});

  @override
  State<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends State<LeaderboardPage> {
  List<dynamic> players = [];
  bool isLoading = true;

  // A tua API no Render
  final String apiUrl = "https://tercas-fc-api.onrender.com/table/";

  @override
  void initState() {
    super.initState();
    fetchLeaderboard();
  }

  // Função para ir buscar os dados (O equivalente ao requests.get do Python)
  Future<void> fetchLeaderboard() async {
    try {
      final response = await http.get(Uri.parse(apiUrl));

      if (response.statusCode == 200) {
        setState(() {
          players = json.decode(response.body); // Converte JSON para Lista
          isLoading = false;
        });
      } else {
        throw Exception('Falha ao carregar tabela');
      }
    } catch (e) {
      print("Erro: $e");
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Classificação 🏆",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.green[900],
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() {
                isLoading = true;
              });
              fetchLeaderboard();
            },
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator()) // Roda de carregar
          : players.isEmpty
          ? const Center(child: Text("Sem dados ou erro de conexão."))
          : SingleChildScrollView(
              scrollDirection: Axis.vertical,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columnSpacing: 20,
                  headingRowColor: MaterialStateProperty.all(Colors.grey[900]),
                  columns: const [
                    DataColumn(
                      label: Text(
                        '#',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                    DataColumn(
                      label: Text(
                        'Nome',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                    DataColumn(
                      label: Text(
                        'P',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.yellow,
                        ),
                      ),
                    ),
                    DataColumn(
                      label: Text(
                        'J',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                    DataColumn(
                      label: Text('V', style: TextStyle(color: Colors.green)),
                    ),
                    DataColumn(
                      label: Text('E', style: TextStyle(color: Colors.blue)),
                    ),
                    DataColumn(
                      label: Text('D', style: TextStyle(color: Colors.red)),
                    ),
                  ],
                  rows: List<DataRow>.generate(players.length, (index) {
                    final player = players[index];
                    final isFixed = player['is_fixed'] ?? false;
                    final name = isFixed
                        ? "${player['name']} (F)"
                        : player['name'];

                    return DataRow(
                      cells: [
                        DataCell(Text((index + 1).toString())),
                        DataCell(
                          Text(
                            name,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                        DataCell(
                          Text(
                            player['points'].toString(),
                            style: const TextStyle(
                              color: Colors.yellow,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        DataCell(Text(player['games_played'].toString())),
                        DataCell(
                          Text(
                            player['wins'].toString(),
                            style: const TextStyle(color: Colors.green),
                          ),
                        ),
                        DataCell(
                          Text(
                            player['draws'].toString(),
                            style: const TextStyle(color: Colors.blue),
                          ),
                        ),
                        DataCell(
                          Text(
                            player['losses'].toString(),
                            style: const TextStyle(color: Colors.red),
                          ),
                        ),
                      ],
                    );
                  }),
                ),
              ),
            ),
    );
  }
}
