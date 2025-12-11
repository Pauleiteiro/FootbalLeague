class Match {
  final int id;
  final String date;
  final String time;
  final String location;
  final String opponent;
  final int confirmedPlayers;
  final bool isOpen;
  final DateTime? closeDate;

  Match({
    required this.id,
    required this.date,
    required this.time,
    required this.location,
    required this.opponent,
    required this.confirmedPlayers,
    required this.isOpen,
    this.closeDate,
  });

  factory Match.fromJson(Map<String, dynamic> json) {
    return Match(
      id: json['id'],
      date: json['date'] ?? "Data a definir",
      time: json['time'] ?? "21:00",
      location: json['location'] ?? "Campo Principal",
      opponent: json['opponent'] ?? "Treino",
      confirmedPlayers: json['confirmed_players'] ?? 0,
      isOpen: json['is_open'] ?? false,
      closeDate: json['close_date'] != null
          ? DateTime.parse(json['close_date'])
          : null,
    );
  }
}
