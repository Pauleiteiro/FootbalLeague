import 'package:flutter/material.dart';
import '../models/player.dart';
import '../services/api_service.dart';
import "../models/match.dart";
import "../widgets/match_card.dart";

class LeaderboardScreen extends StatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  State<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends State<LeaderboardScreen> {
  // Vamos buscar duas coisas: Lista de Jogadores e o Próximo Jogo (que pode ser nulo)
  late Future<List<Player>> futurePlayers;
  late Future<Match?> futureMatch; // <--- Novo

  final ApiService api = ApiService();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    setState(() {
      futurePlayers = api.getLeaderboard();
      futureMatch = api.getNextMatch(); // <--- Inicia o pedido do jogo
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Terças FC ⚽",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.green[900],
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: Column(
        children: [
          // 1. ZONA DO CARTÃO DE JOGO (FutureBuilder independente)
          FutureBuilder<Match?>(
            future: futureMatch,
            builder: (context, snapshot) {
              // Se estiver a carregar ou der erro, ou se for null (sem jogo), escondemos o cartão
              if (!snapshot.hasData || snapshot.data == null) {
                // Podes retornar um Container vazio para esconder, ou um texto "Sem jogos"
                return const SizedBox.shrink();
              }
              // Se houver jogo, mostra o cartão com os dados!
              return MatchCard(match: snapshot.data!);
            },
          ),

          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 5),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "CLASSIFICAÇÃO",
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.grey,
                ),
              ),
            ),
          ),

          // 2. A TABELA (Igual ao que já tinhas)
          Expanded(
            child: FutureBuilder<List<Player>>(
              future: futurePlayers,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError) {
                  return Center(child: Text("Erro ao carregar tabela"));
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return const Center(child: Text("Sem dados."));
                }

                // ... (O teu código da DataTable continua aqui igualzinho) ...
                return SingleChildScrollView(
                  scrollDirection: Axis.vertical,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columnSpacing: 20,
                      headingRowColor: MaterialStateProperty.all(
                        Colors.grey[900],
                      ),
                      columns: const [
                        DataColumn(label: Text('#')),
                        DataColumn(label: Text('Nome')),
                        DataColumn(
                          label: Text(
                            'P',
                            style: TextStyle(color: Colors.yellow),
                          ),
                        ),
                        DataColumn(label: Text('J')),
                        DataColumn(
                          label: Text(
                            'V',
                            style: TextStyle(color: Colors.green),
                          ),
                        ),
                        DataColumn(
                          label: Text(
                            'E',
                            style: TextStyle(color: Colors.blue),
                          ),
                        ),
                        DataColumn(
                          label: Text('D', style: TextStyle(color: Colors.red)),
                        ),
                      ],
                      rows: List<DataRow>.generate(snapshot.data!.length, (
                        index,
                      ) {
                        final player = snapshot.data![index];
                        final nameDisplay = player.isFixed
                            ? "${player.name} (F)"
                            : player.name;
                        return DataRow(
                          cells: [
                            DataCell(Text((index + 1).toString())),
                            DataCell(
                              Text(
                                nameDisplay,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            DataCell(
                              Text(
                                player.points.toString(),
                                style: const TextStyle(
                                  color: Colors.yellow,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            DataCell(Text(player.games_played.toString())),
                            DataCell(
                              Text(
                                player.wins.toString(),
                                style: const TextStyle(color: Colors.green),
                              ),
                            ),
                            DataCell(
                              Text(
                                player.draws.toString(),
                                style: const TextStyle(color: Colors.blue),
                              ),
                            ),
                            DataCell(
                              Text(
                                player.losses.toString(),
                                style: const TextStyle(color: Colors.red),
                              ),
                            ),
                          ],
                        );
                      }),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
