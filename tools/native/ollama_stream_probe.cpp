// Minimal Windows-only Ollama streaming latency probe.
//
// Build from the repo root with MinGW:
//   g++ tools/native/ollama_stream_probe.cpp -O2 -lws2_32 -o tools/native/ollama_stream_probe.exe
//
// Run:
//   tools\native\ollama_stream_probe.exe gemma4:e2b-it-q4_K_M
//
// This measures native HTTP streaming overhead only. Ollama still performs the
// model inference in its own llama.cpp runtime.

#define WIN32_LEAN_AND_MEAN

#include <winsock2.h>
#include <ws2tcpip.h>

#include <chrono>
#include <iostream>
#include <sstream>
#include <string>

namespace {

std::string json_escape(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size() + 8);
    for (char ch : value) {
        if (ch == '\\' || ch == '"') {
            escaped.push_back('\\');
        }
        if (ch == '\n') {
            escaped += "\\n";
        } else {
            escaped.push_back(ch);
        }
    }
    return escaped;
}

long long elapsed_ms(std::chrono::steady_clock::time_point started) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now() - started)
        .count();
}

}  // namespace

int main(int argc, char** argv) {
    const std::string model = argc > 1 ? argv[1] : "gemma4:e2b-it-q4_K_M";
    const std::string prompt =
        argc > 2 ? argv[2]
                 : "Cliente: Quiero una mesa cerca de la ventana porque viene una "
                   "persona mayor. Respuesta telefonica breve:";

    WSADATA wsa_data;
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        std::cerr << "WSAStartup failed\n";
        return 1;
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        std::cerr << "socket failed\n";
        WSACleanup();
        return 1;
    }

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_port = htons(11434);
    address.sin_addr.s_addr = inet_addr("127.0.0.1");

    const auto started = std::chrono::steady_clock::now();
    if (connect(sock, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == SOCKET_ERROR) {
        std::cerr << "connect failed. Is Ollama running?\n";
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    const std::string body =
        std::string("{") +
        "\"model\":\"" + json_escape(model) + "\"," +
        "\"stream\":true,\"think\":false,\"keep_alive\":\"30m\"," +
        "\"system\":\"Responde como agente telefonico de restaurante. Maximo 25 palabras.\"," +
        "\"prompt\":\"" + json_escape(prompt) + "\"," +
        "\"options\":{\"num_predict\":48,\"num_ctx\":768,\"temperature\":0.2,\"top_p\":0.85,\"top_k\":20}" +
        "}";

    std::ostringstream request;
    request << "POST /api/generate HTTP/1.1\r\n"
            << "Host: 127.0.0.1:11434\r\n"
            << "Content-Type: application/json\r\n"
            << "Content-Length: " << body.size() << "\r\n"
            << "Connection: close\r\n\r\n"
            << body;

    const std::string raw_request = request.str();
    send(sock, raw_request.data(), static_cast<int>(raw_request.size()), 0);

    char buffer[4096];
    bool first_response_seen = false;
    std::string response;
    while (true) {
        int received = recv(sock, buffer, sizeof(buffer), 0);
        if (received <= 0) {
            break;
        }
        response.append(buffer, buffer + received);
        if (!first_response_seen && response.find("\"response\"") != std::string::npos) {
            first_response_seen = true;
            std::cout << "first_response_marker_ms=" << elapsed_ms(started) << "\n";
        }
        if (response.find(".") != std::string::npos && first_response_seen) {
            std::cout << "first_period_seen_ms=" << elapsed_ms(started) << "\n";
            break;
        }
    }

    std::cout << "total_probe_ms=" << elapsed_ms(started) << "\n";
    closesocket(sock);
    WSACleanup();
    return 0;
}
