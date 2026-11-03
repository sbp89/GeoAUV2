"""
Esquemas Pydantic v2 para los 9 pasos de GeoAUV2 (GeoMineral AI v2)
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CustomSpectralWeights(BaseModel):
    alunita: Optional[float] = None
    caolinita: Optional[float] = None
    sericita: Optional[float] = None
    silice: Optional[float] = None
    cuarzo: Optional[float] = None
    gossan: Optional[float] = None
    fe3: Optional[float] = None
    clorita: Optional[float] = None
    s2_arcilla_cai: Optional[float] = None
    s2_feox: Optional[float] = None


class IntegratedWeights(BaseModel):
    favorability: float = Field(default=0.42, ge=0.0, le=1.0)
    structural: float = Field(default=0.26, ge=0.0, le=1.0)
    geological_sgc: float = Field(default=0.20, ge=0.0, le=1.0)
    geophysical: float = Field(default=0.12, ge=0.0, le=1.0)


class TrainingSampleInput(BaseModel):
    class_id: int = Field(ge=1, le=20)
    class_name: str
    class_color: str = "#f39c12"
    lat: float
    lon: float


class AnalysisRequest(BaseModel):
    preset_id: Optional[str] = None
    lat: float = Field(default=7.0792, ge=-90.0, le=90.0)
    lon: float = Field(default=-74.6988, ge=-180.0, le=180.0)
    bbox: Optional[List[float]] = None
    roi_size_km: float = Field(default=4.0, ge=0.5, le=25.0)

    # Paso 1: Configuración Multisensor y Máscaras
    sensor_mode: str = Field(default="multisensor")  # multisensor | sentinel2 | aster
    start_date: str = Field(default="2020-01-01")
    end_date: str = Field(default="2026-10-31")
    cloud_cover_max: float = Field(default=20.0, ge=0.0, le=100.0)
    mask_vegetation: bool = True
    ndvi_threshold: float = Field(default=0.45, ge=-0.2, le=0.95)
    mask_water: bool = True
    ndwi_threshold: float = Field(default=0.15, ge=-0.5, le=0.9)
    mask_shadows: bool = True

    # Paso 2: Normalización Robusta
    norm_method: str = Field(default="p2_p98")  # p2_p98 | p5_p95 | minmax

    # Paso 3: Stack Multibanda ML
    selected_stack_keys: Optional[List[str]] = None

    # Paso 4: IA / Machine Learning
    ml_method: str = Field(default="kmeans")  # kmeans | random_forest | svm | cosine_similarity
    n_clusters: int = Field(default=6, ge=2, le=12)
    apply_majority_filter: bool = True
    majority_window: int = Field(default=3, ge=3, le=5)
    apply_sieve_filter: bool = True
    sieve_min_pixels: int = Field(default=6, ge=1, le=50)
    training_samples: Optional[List[TrainingSampleInput]] = None

    # Paso 5 & 6: Favorabilidad y Prospectividad Integrada
    deposit_model: str = Field(default="orogenico_vetas")
    strict_nan: bool = False
    custom_spectral_weights: Optional[Dict[str, float]] = None
    integrated_weights: Optional[IntegratedWeights] = None

    # Paso 7 & 8: Targets Priorizados y Validación Estadística
    target_threshold: float = Field(default=0.68, ge=0.30, le=0.95)
    min_target_area_ha: float = Field(default=1.5, ge=0.1, le=100.0)
    validation_buffer_m: float = Field(default=250.0, ge=50.0, le=2000.0)
    known_occurrences: Optional[List[Dict[str, Any]]] = None

    # Persistencia opcional en Supabase
    save_to_cloud: bool = True
    project_name: Optional[str] = None


class MagnetometryPointInput(BaseModel):
    lat: float
    lon: float
    bx: float
    by: float
    bz: float
    elevation_m: Optional[float] = 1500.0
    station_id: Optional[str] = None


class MagnetometryRequest(BaseModel):
    survey_name: str = "Campaña Magnetometría Terrestre — Veta Hidrotermal"
    district_name: Optional[str] = "Segovia - Remedios"
    center_lat: float = 7.0792
    center_lon: float = -74.6988
    use_demo_dataset: bool = True
    points: Optional[List[MagnetometryPointInput]] = None
    save_to_cloud: bool = True


class GEEScriptRequest(BaseModel):
    template_type: str = Field(default="multisensor_6modulos")  # sentinel2_descarga | multisensor_6modulos | dzetsaka_rf_svm
    roi_name: str = "Area_Exploracion_GeoAUV2"
    bbox: List[float] = Field(default_factory=lambda: [-74.7188, 7.0592, -74.6788, 7.0992])
    start_date: str = "2023-01-01"
    end_date: str = "2026-10-01"
    cloud_cover_max: float = 15.0
    ndvi_threshold: float = 0.45
    deposit_model: str = "epitermal_as"


class ProjectSaveRequest(BaseModel):
    name: str
    district_code: Optional[str] = None
    sensor_mode: str = "multisensor"
    deposit_model: str = "epitermal_as"
    center_lat: float
    center_lon: float
    roi_size_km: float = 4.0
    bbox: List[float]
    config_json: Dict[str, Any] = Field(default_factory=dict)
