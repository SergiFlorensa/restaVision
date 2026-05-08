// Local WAV postprocessor for RestaurIA voice output.
//
// Build from the repo root:
//   C:\Users\SERGI\.cargo\bin\rustc.exe tools/native/voice_postprocess.rs -O -o tools/native/voice_postprocess.exe
//
// Run:
//   tools\native\voice_postprocess.exe input.wav output.wav clarity
//
// Presets:
//   clarity: high-pass + light compression + peak normalization.
//   warm:    softer high-pass + lighter compression + peak normalization.
//   phone:   telephone band-pass + stronger compression + peak normalization.

use std::env;
use std::convert::TryInto;
use std::fs;
use std::io::{Error, ErrorKind, Result};

#[derive(Clone, Copy)]
struct Preset {
    name: &'static str,
    high_pass_hz: f32,
    low_pass_hz: Option<f32>,
    threshold: f32,
    ratio: f32,
    makeup_gain: f32,
    target_peak: f32,
}

const CLARITY: Preset = Preset {
    name: "clarity",
    high_pass_hz: 90.0,
    low_pass_hz: None,
    threshold: 0.22,
    ratio: 2.4,
    makeup_gain: 1.18,
    target_peak: 0.92,
};

const WARM: Preset = Preset {
    name: "warm",
    high_pass_hz: 70.0,
    low_pass_hz: None,
    threshold: 0.28,
    ratio: 1.8,
    makeup_gain: 1.08,
    target_peak: 0.9,
};

const PHONE: Preset = Preset {
    name: "phone",
    high_pass_hz: 300.0,
    low_pass_hz: Some(3400.0),
    threshold: 0.18,
    ratio: 3.2,
    makeup_gain: 1.28,
    target_peak: 0.9,
};

struct WavFile {
    channels: u16,
    sample_rate: u32,
    bits_per_sample: u16,
    samples: Vec<i16>,
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: voice_postprocess <input.wav> <output.wav> [clarity|warm|phone]");
        return Err(Error::new(ErrorKind::InvalidInput, "missing arguments"));
    }
    let input_path = &args[1];
    let output_path = &args[2];
    let preset = preset_from_name(args.get(3).map(String::as_str).unwrap_or("clarity"))?;

    let input = fs::read(input_path)?;
    let wav = read_pcm16_wav(&input)?;
    let processed = process_samples(&wav.samples, wav.channels, wav.sample_rate, preset);
    let output = write_pcm16_wav(wav.channels, wav.sample_rate, wav.bits_per_sample, &processed);
    fs::write(output_path, output)?;

    println!(
        "{{\"preset\":\"{}\",\"sample_rate_hz\":{},\"channels\":{},\"samples\":{}}}",
        preset.name,
        wav.sample_rate,
        wav.channels,
        processed.len()
    );
    Ok(())
}

fn preset_from_name(name: &str) -> Result<Preset> {
    match name.trim().to_lowercase().as_str() {
        "clarity" => Ok(CLARITY),
        "warm" => Ok(WARM),
        "phone" | "telephone" => Ok(PHONE),
        other => Err(Error::new(
            ErrorKind::InvalidInput,
            format!("unsupported voice postprocess preset: {}", other),
        )),
    }
}

fn read_pcm16_wav(bytes: &[u8]) -> Result<WavFile> {
    if bytes.len() < 44 || &bytes[0..4] != b"RIFF" || &bytes[8..12] != b"WAVE" {
        return Err(Error::new(ErrorKind::InvalidData, "not a RIFF/WAVE file"));
    }

    let mut offset = 12usize;
    let mut channels = None;
    let mut sample_rate = None;
    let mut bits_per_sample = None;
    let mut audio_format = None;
    let mut data_range = None;

    while offset + 8 <= bytes.len() {
        let chunk_id = &bytes[offset..offset + 4];
        let chunk_size = u32::from_le_bytes(bytes[offset + 4..offset + 8].try_into().unwrap()) as usize;
        let chunk_start = offset + 8;
        let chunk_end = chunk_start.saturating_add(chunk_size);
        if chunk_end > bytes.len() {
            return Err(Error::new(ErrorKind::InvalidData, "invalid WAV chunk size"));
        }

        if chunk_id == b"fmt " {
            if chunk_size < 16 {
                return Err(Error::new(ErrorKind::InvalidData, "invalid fmt chunk"));
            }
            audio_format = Some(u16::from_le_bytes(
                bytes[chunk_start..chunk_start + 2].try_into().unwrap(),
            ));
            channels = Some(u16::from_le_bytes(
                bytes[chunk_start + 2..chunk_start + 4].try_into().unwrap(),
            ));
            sample_rate = Some(u32::from_le_bytes(
                bytes[chunk_start + 4..chunk_start + 8].try_into().unwrap(),
            ));
            bits_per_sample = Some(u16::from_le_bytes(
                bytes[chunk_start + 14..chunk_start + 16].try_into().unwrap(),
            ));
        } else if chunk_id == b"data" {
            data_range = Some((chunk_start, chunk_end));
        }

        offset = chunk_end + (chunk_size % 2);
    }

    if audio_format != Some(1) {
        return Err(Error::new(ErrorKind::InvalidData, "only PCM WAV is supported"));
    }
    if bits_per_sample != Some(16) {
        return Err(Error::new(ErrorKind::InvalidData, "only PCM16 WAV is supported"));
    }
    let (start, end) =
        data_range.ok_or_else(|| Error::new(ErrorKind::InvalidData, "missing data chunk"))?;
    let mut samples = Vec::with_capacity((end - start) / 2);
    let mut index = start;
    while index + 2 <= end {
        samples.push(i16::from_le_bytes(bytes[index..index + 2].try_into().unwrap()));
        index += 2;
    }

    Ok(WavFile {
        channels: channels.ok_or_else(|| Error::new(ErrorKind::InvalidData, "missing channels"))?,
        sample_rate: sample_rate
            .ok_or_else(|| Error::new(ErrorKind::InvalidData, "missing sample rate"))?,
        bits_per_sample: bits_per_sample
            .ok_or_else(|| Error::new(ErrorKind::InvalidData, "missing bit depth"))?,
        samples,
    })
}

fn process_samples(samples: &[i16], channels: u16, sample_rate: u32, preset: Preset) -> Vec<i16> {
    let channel_count = channels as usize;
    let mut processed: Vec<f32> = samples.iter().map(|sample| *sample as f32 / 32768.0).collect();

    high_pass(&mut processed, channel_count, sample_rate, preset.high_pass_hz);
    if let Some(cutoff) = preset.low_pass_hz {
        low_pass(&mut processed, channel_count, sample_rate, cutoff);
    }
    compress(&mut processed, preset.threshold, preset.ratio, preset.makeup_gain);
    normalize_peak(&mut processed, preset.target_peak);

    processed
        .iter()
        .map(|sample| {
            let clipped = sample.clamp(-1.0, 1.0);
            (clipped * 32767.0).round() as i16
        })
        .collect()
}

fn high_pass(samples: &mut [f32], channels: usize, sample_rate: u32, cutoff_hz: f32) {
    if cutoff_hz <= 0.0 {
        return;
    }
    let dt = 1.0 / sample_rate as f32;
    let rc = 1.0 / (2.0 * std::f32::consts::PI * cutoff_hz);
    let alpha = rc / (rc + dt);
    for channel in 0..channels {
        let mut previous_y = 0.0;
        let mut previous_x = 0.0;
        let mut index = channel;
        while index < samples.len() {
            let x = samples[index];
            let y = alpha * (previous_y + x - previous_x);
            samples[index] = y;
            previous_y = y;
            previous_x = x;
            index += channels;
        }
    }
}

fn low_pass(samples: &mut [f32], channels: usize, sample_rate: u32, cutoff_hz: f32) {
    let dt = 1.0 / sample_rate as f32;
    let rc = 1.0 / (2.0 * std::f32::consts::PI * cutoff_hz);
    let alpha = dt / (rc + dt);
    for channel in 0..channels {
        let mut previous = 0.0;
        let mut index = channel;
        while index < samples.len() {
            previous += alpha * (samples[index] - previous);
            samples[index] = previous;
            index += channels;
        }
    }
}

fn compress(samples: &mut [f32], threshold: f32, ratio: f32, makeup_gain: f32) {
    for sample in samples {
        let sign = sample.signum();
        let magnitude = sample.abs();
        let compressed = if magnitude > threshold {
            threshold + (magnitude - threshold) / ratio
        } else {
            magnitude
        };
        *sample = sign * compressed * makeup_gain;
    }
}

fn normalize_peak(samples: &mut [f32], target_peak: f32) {
    let peak = samples
        .iter()
        .fold(0.0f32, |current, sample| current.max(sample.abs()));
    if peak > 0.0001 {
        let gain = target_peak / peak;
        for sample in samples {
            *sample *= gain;
        }
    }
}

fn write_pcm16_wav(channels: u16, sample_rate: u32, bits_per_sample: u16, samples: &[i16]) -> Vec<u8> {
    let data_size = (samples.len() * 2) as u32;
    let byte_rate = sample_rate * channels as u32 * bits_per_sample as u32 / 8;
    let block_align = channels * bits_per_sample / 8;
    let riff_size = 36 + data_size;
    let mut output = Vec::with_capacity(44 + data_size as usize);

    output.extend_from_slice(b"RIFF");
    output.extend_from_slice(&riff_size.to_le_bytes());
    output.extend_from_slice(b"WAVEfmt ");
    output.extend_from_slice(&16u32.to_le_bytes());
    output.extend_from_slice(&1u16.to_le_bytes());
    output.extend_from_slice(&channels.to_le_bytes());
    output.extend_from_slice(&sample_rate.to_le_bytes());
    output.extend_from_slice(&byte_rate.to_le_bytes());
    output.extend_from_slice(&block_align.to_le_bytes());
    output.extend_from_slice(&bits_per_sample.to_le_bytes());
    output.extend_from_slice(b"data");
    output.extend_from_slice(&data_size.to_le_bytes());
    for sample in samples {
        output.extend_from_slice(&sample.to_le_bytes());
    }
    output
}
