class Match {
  final int id;
  final String date;
  final String time;
  final String location;
  final String opponent;
  final int confirmedPlayers;

  Match({
    required this.id,
    required this.date,
    required this.time,
    required this.location,
    required this.opponent,
    required this.confirmedPlayers,
  });

  factory Match.fromJson(Map<String, dynamic> json) {
    return Match(
      id: json['id'],
      date: json['date'] ?? "Data a definir",
      time: json['time'] ?? "21:00",
      location: json['location'] ?? "Campo Principal",
      opponent: json['opponent'] ?? "Treino",
      confirmedPlayers: json['confirmed_players'] ?? 0,
    );
  }
}
