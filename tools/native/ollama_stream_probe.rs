// Minimal Ollama streaming latency probe in Rust.
//
// Build from the repo root:
//   C:\Users\SERGI\.cargo\bin\rustc.exe tools/native/ollama_stream_probe.rs -O -o tools/native/ollama_stream_probe_rust.exe
//
// Run:
//   tools\native\ollama_stream_probe_rust.exe gemma4:e2b-it-q4_K_M
//   tools\native\ollama_stream_probe_rust.exe gemma4:e2b-it-q4_K_M "Cliente: ..." --num-thread 4 --num-ctx 256 --num-predict 24
//
// This uses only Rust stdlib. Ollama still performs inference in its own runtime.

use std::env;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Instant;

fn json_escape(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
}

fn elapsed_ms(started: Instant) -> u128 {
    started.elapsed().as_millis()
}

fn flag_value<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
    args.iter()
        .position(|arg| arg == flag)
        .and_then(|index| args.get(index + 1))
        .map(String::as_str)
}

fn parse_u32_flag(args: &[String], flag: &str, default_value: u32) -> u32 {
    flag_value(args, flag)
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(default_value)
}

fn extract_response_tokens(buffer: &str, consumed_lines: &mut usize) -> Vec<String> {
    let lines: Vec<&str> = buffer.lines().collect();
    let mut tokens = Vec::new();
    for line in lines.iter().skip(*consumed_lines) {
        if let Some(token) = extract_response_token(line) {
            tokens.push(token);
        }
    }
    *consumed_lines = lines.len();
    tokens
}

fn extract_response_token(line: &str) -> Option<String> {
    let marker = "\"response\":\"";
    let start = line.find(marker)? + marker.len();
    let mut escaped = false;
    let mut token = String::new();
    for character in line[start..].chars() {
        if escaped {
            token.push(match character {
                'n' => '\n',
                'r' => '\r',
                't' => '\t',
                '"' => '"',
                '\\' => '\\',
                other => other,
            });
            escaped = false;
            continue;
        }
        if character == '\\' {
            escaped = true;
            continue;
        }
        if character == '"' {
            return Some(token);
        }
        token.push(character);
    }
    None
}

fn main() -> std::io::Result<()> {
    let args: Vec<String> = env::args().collect();
    let model = args
        .get(1)
        .map(String::as_str)
        .unwrap_or("gemma4:e2b-it-q4_K_M");
    let prompt = args.get(2).map(String::as_str).unwrap_or(
        "Cliente: Quiero una mesa cerca de la ventana porque viene una persona mayor. Respuesta telefonica breve:",
    );
    let num_thread = parse_u32_flag(&args, "--num-thread", 4);
    let num_ctx = parse_u32_flag(&args, "--num-ctx", 256);
    let num_predict = parse_u32_flag(&args, "--num-predict", 24);

    let started = Instant::now();
    let mut stream = TcpStream::connect("127.0.0.1:11434")?;
    let body = format!(
        concat!(
            "{{",
            "\"model\":\"{}\",",
            "\"stream\":true,",
            "\"think\":false,",
            "\"keep_alive\":\"30m\",",
            "\"system\":\"Responde como agente telefonico de restaurante en Espana. Maximo 25 palabras.\",",
            "\"prompt\":\"{}\",",
            "\"options\":{{\"num_thread\":{},\"num_predict\":{},\"num_ctx\":{},\"temperature\":0.1,\"top_p\":0.8,\"top_k\":20,\"stop\":[\"\\n\"]}}",
            "}}"
        ),
        json_escape(model),
        json_escape(prompt),
        num_thread,
        num_predict,
        num_ctx
    );
    let request = format!(
        concat!(
            "POST /api/generate HTTP/1.1\r\n",
            "Host: 127.0.0.1:11434\r\n",
            "Content-Type: application/json\r\n",
            "Content-Length: {}\r\n",
            "Connection: close\r\n\r\n",
            "{}"
        ),
        body.len(),
        body
    );
    stream.write_all(request.as_bytes())?;

    let mut buffer = [0_u8; 4096];
    let mut response = String::new();
    let mut collected = String::new();
    let mut first_response_seen = false;
    let mut consumed_lines = 0_usize;
    println!(
        "settings model={} num_thread={} num_ctx={} num_predict={}",
        model, num_thread, num_ctx, num_predict
    );
    loop {
        let received = stream.read(&mut buffer)?;
        if received == 0 {
            break;
        }
        response.push_str(&String::from_utf8_lossy(&buffer[..received]));
        for token in extract_response_tokens(&response, &mut consumed_lines) {
            if !first_response_seen {
                first_response_seen = true;
                println!("first_response_marker_ms={}", elapsed_ms(started));
            }
            collected.push_str(&token);
        }
        if first_response_seen && collected.contains('.') {
            println!("first_period_seen_ms={}", elapsed_ms(started));
            break;
        }
    }
    println!("total_probe_ms={}", elapsed_ms(started));
    println!("collected={}", collected.trim());
    Ok(())
}
