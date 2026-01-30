package main

/*
#define FNL_IMPL
#include "FastNoiseLite.h"
#include <stdlib.h>
*/
import "C"
import (
	"encoding/json"
	"fmt"
	"image"
	"image/png"
	"log"
	"net/http"
	"os"
)

// NoiseConfig 噪声配置结构
type NoiseConfig struct {
	Width          int     `json:"width"`
	Height         int     `json:"height"`
	NoiseType      string  `json:"noise_type"`      // "opensimplex2", "perlin", "cellular", "value"
	Seed           int     `json:"seed"`
	Frequency      float32 `json:"frequency"`
	FractalType    string  `json:"fractal_type"`    // "none", "fbm", "ridged", "pingpong"
	FractalOctaves int     `json:"fractal_octaves"`
	FractalLacunarity float32 `json:"fractal_lacunarity"`
	FractalGain    float32 `json:"fractal_gain"`
	CellularDistanceFunc string `json:"cellular_distance_func"` // "euclidean", "manhattan", "hybrid"
	CellularReturnType   string `json:"cellular_return_type"`   // "distance", "distance2"
	OutputPath     string  `json:"output_path"`
}

// 默认配置
func defaultConfig() NoiseConfig {
	return NoiseConfig{
		Width:          512,
		Height:         512,
		NoiseType:      "opensimplex2",
		Seed:           1337,
		Frequency:      0.01,
		FractalType:    "fbm",
		FractalOctaves: 6,
		FractalLacunarity: 2.0,
		FractalGain:    0.5,
		CellularDistanceFunc: "euclidean",
		CellularReturnType:   "distance",
		OutputPath:     "/tmp/noise_output.png",
	}
}

// GenerateNoise 生成噪声纹理
func GenerateNoise(config NoiseConfig) ([]byte, error) {
	// 创建FastNoiseLite状态
	state := C.fnlCreateState()
	state.seed = C.int(config.Seed)
	
	// 设置噪声类型
	switch config.NoiseType {
	case "opensimplex2":
		state.noise_type = C.FNL_NOISE_OPENSIMPLEX2
	case "opensimplex2s":
		state.noise_type = C.FNL_NOISE_OPENSIMPLEX2S
	case "perlin":
		state.noise_type = C.FNL_NOISE_PERLIN
	case "cellular":
		state.noise_type = C.FNL_NOISE_CELLULAR
	case "value":
		state.noise_type = C.FNL_NOISE_VALUE
	case "value_cubic":
		state.noise_type = C.FNL_NOISE_VALUE_CUBIC
	default:
		state.noise_type = C.FNL_NOISE_OPENSIMPLEX2
	}
	
	// 设置频率
	state.frequency = C.FNLfloat(config.Frequency)
	
	// 设置分形类型
	switch config.FractalType {
	case "none":
		state.fractal_type = C.FNL_FRACTAL_NONE
	case "fbm":
		state.fractal_type = C.FNL_FRACTAL_FBM
	case "ridged":
		state.fractal_type = C.FNL_FRACTAL_RIDGED
	case "pingpong":
		state.fractal_type = C.FNL_FRACTAL_PINGPONG
	default:
		state.fractal_type = C.FNL_FRACTAL_FBM
	}
	
	// 设置分形参数
	state.octaves = C.int(config.FractalOctaves)
	state.lacunarity = C.FNLfloat(config.FractalLacunarity)
	state.gain = C.FNLfloat(config.FractalGain)
	
	// 设置Cellular参数
	switch config.CellularDistanceFunc {
	case "euclidean":
		state.cellular_distance_func = C.FNL_CELLULAR_DISTANCE_EUCLIDEAN
	case "manhattan":
		state.cellular_distance_func = C.FNL_CELLULAR_DISTANCE_MANHATTAN
	case "hybrid":
		state.cellular_distance_func = C.FNL_CELLULAR_DISTANCE_HYBRID
	default:
		state.cellular_distance_func = C.FNL_CELLULAR_DISTANCE_EUCLIDEAN
	}
	
	switch config.CellularReturnType {
	case "cellvalue":
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_CELLVALUE
	case "distance":
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_DISTANCE
	case "distance2":
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_DISTANCE2
	case "distance2add":
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_DISTANCE2ADD
	case "distance2sub":
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_DISTANCE2SUB
	default:
		state.cellular_return_type = C.FNL_CELLULAR_RETURN_TYPE_DISTANCE
	}
	
	// 生成噪声数据
	width := config.Width
	height := config.Height
	noiseData := make([]byte, width*height)
	
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			// 获取噪声值 (范围 -1 到 1)
			noiseValue := float32(C.fnlGetNoise2D(&state, C.FNLfloat(x), C.FNLfloat(y)))
			
			// 归一化到 0-255
			normalized := uint8((noiseValue + 1.0) * 127.5)
			noiseData[y*width+x] = normalized
		}
	}
	
	return noiseData, nil
}

// SaveNoiseImage 保存噪声为PNG图片
func SaveNoiseImage(data []byte, width, height int, path string) error {
	// 创建灰度图像
	img := image.NewGray(image.Rect(0, 0, width, height))
	copy(img.Pix, data)
	
	// 保存为PNG
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()
	
	return png.Encode(file, img)
}

// HTTP处理器
func generateNoiseHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// 解析JSON配置
	var config NoiseConfig
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}
	
	// 设置默认值
	if config.Width == 0 {
		config.Width = 512
	}
	if config.Height == 0 {
		config.Height = 512
	}
	if config.Frequency == 0 {
		config.Frequency = 0.01
	}
	if config.FractalOctaves == 0 {
		config.FractalOctaves = 6
	}
	if config.FractalLacunarity == 0 {
		config.FractalLacunarity = 2.0
	}
	if config.FractalGain == 0 {
		config.FractalGain = 0.5
	}
	
	// 生成噪声
	noiseData, err := GenerateNoise(config)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to generate noise: %v", err), http.StatusInternalServerError)
		return
	}
	
	// 返回原始字节数据
	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("X-Width", fmt.Sprintf("%d", config.Width))
	w.Header().Set("X-Height", fmt.Sprintf("%d", config.Height))
	w.Write(noiseData)
}

// 健康检查处理器
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "OK")
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	http.HandleFunc("/generate", generateNoiseHandler)
	http.HandleFunc("/health", healthHandler)
	
	log.Printf("FastNoiseLite Go Service starting on port %s...", port)
	log.Printf("Endpoints:")
	log.Printf("  POST /generate - Generate noise texture")
	log.Printf("  GET  /health   - Health check")
	
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal(err)
	}
}
