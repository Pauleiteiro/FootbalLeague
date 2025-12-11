import 'dart:async'; // <--- Necessário para o Timer
import 'package:flutter/material.dart';
import '../models/match.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class MatchCard extends StatefulWidget {
  final Match match;
  final VoidCallback? onUpdate;

  const MatchCard({super.key, required this.match, this.onUpdate});

  @override
  State<MatchCard> createState() => _MatchCardState();
}

class _MatchCardState extends State<MatchCard> {
  Timer? _timer;
  String _timeLeft = "";

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer
        ?.cancel(); // Matar o timer quando saímos do ecrã para não gastar bateria
    super.dispose();
  }

  void _startTimer() {
    // Só vale a pena contar se estiver aberto e tivermos uma data de fecho
    if (!widget.match.isOpen || widget.match.closeDate == null) {
      setState(() => _timeLeft = "Encerrado");
      return;
    }

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final now = DateTime.now();
      final difference = widget.match.closeDate!.difference(now);

      if (difference.isNegative) {
        timer.cancel();
        setState(() => _timeLeft = "Tempo Esgotado!");
      } else {
        // Formatar para HH:MM:SS
        final hours = difference.inHours.toString().padLeft(2, '0');
        final minutes = (difference.inMinutes % 60).toString().padLeft(2, '0');
        final seconds = (difference.inSeconds % 60).toString().padLeft(2, '0');

        setState(() {
          _timeLeft = "$hours:$minutes:$seconds";
        });
      }
    });
  }

  void _vote(BuildContext context, String status) async {
    final user = await AuthService().getUserSession();
    if (user == null) return;

    final api = ApiService();
    final success = await api.updateAttendance(
      widget.match.id,
      user['id'],
      status,
    );

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            status == 'going' ? "Confirmado! ⚽" : "Falhaste a convocatória. 😢",
          ),
          backgroundColor: status == 'going' ? Colors.green : Colors.red,
        ),
      );
      if (widget.onUpdate != null) widget.onUpdate!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.green[900]!, Colors.black],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.green.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        children: [
          // CABEÇALHO COM TIMER
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                "PRÓXIMO JOGO ⚽",
                style: TextStyle(
                  color: Colors.white54,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
              // O NOSSO TIMER AQUI
              if (widget.match.isOpen)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.timer, size: 12, color: Colors.white),
                      const SizedBox(width: 4),
                      Text(
                        _timeLeft,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),

          const SizedBox(height: 15),

          // DETALHES
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.match.date,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    "${widget.match.location} • ${widget.match.opponent}",
                    style: const TextStyle(color: Colors.grey, fontSize: 13),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  widget.match.time,
                  style: const TextStyle(
                    color: Colors.yellow,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const Divider(color: Colors.white24, height: 30),

          // BOTÕES
          if (!widget.match.isOpen)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                "Inscrições encerradas.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white70),
              ),
            )
          else
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _vote(context, 'going'),
                    icon: const Icon(Icons.check_circle, color: Colors.white),
                    label: const Text(
                      "VOU",
                      style: TextStyle(color: Colors.white),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green[700],
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _vote(context, 'not_going'),
                    icon: const Icon(Icons.cancel, color: Colors.white),
                    label: const Text(
                      "NÃO",
                      style: TextStyle(color: Colors.white),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red[900],
                    ),
                  ),
                ),
              ],
            ),

          const SizedBox(height: 10),
          Text(
            "${widget.match.confirmedPlayers} Jogadores confirmados",
            style: const TextStyle(
              color: Colors.grey,
              fontSize: 12,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }
}
