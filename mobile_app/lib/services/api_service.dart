import "dart:convert";
import "package:http/http.dart" as http;
import "../models/player.dart";
import "../models/match.dart";

class ApiService {
  // Link of my API
  static const String baseUrl = "https://tercas-fc-api.onrender.com";

  Future<List<Player>> getLeaderboard() async {
    try {
      final responde = await http.get(Uri.parse("$baseUrl/table"));

      if (responde.statusCode == 200) {
        List<dynamic> body = json.decode(responde.body);
        // Convert json list in a list of player objects
        return body.map((item) => Player.fromJson(item)).toList();
      } else {
        throw Exception("Falha ao carregar tabela: ${responde.statusCode}");
      }
    } catch (e) {
      throw Exception("Erro de conexão: $e");
    }
  }

  Future<Match?> getNextMatch() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/matches/next'));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        // Se a API devolver "id: null", significa que não há jogos
        if (data['id'] == null) {
          return null;
        }

        return Match.fromJson(data);
      } else {
        return null;
      }
    } catch (e) {
      print("Erro ao buscar jogo: $e");
      return null;
    }
  }
}
