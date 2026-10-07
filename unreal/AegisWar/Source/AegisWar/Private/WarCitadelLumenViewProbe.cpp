#include "WarCitadelLumenViewProbe.h"
#include "Dom/JsonObject.h"
#include "DynamicRHI.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeLock.h"
#include "RenderUtils.h"
#include "RHI.h"
#include "SceneInterface.h"
#include "SceneManagement.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    class FProbe final : public FWorldSceneViewExtension
    {
    public:
        FProbe(const FAutoRegister& Registration, UWorld* World)
            : FWorldSceneViewExtension(Registration, World) {}

        void Arm(const FSceneInterface* Scene, const FRenderTarget* Target, const FString& Token)
        {
            FScopeLock Lock(&Mutex);
            ExpectedScene=Scene;ExpectedTarget=Target;Nonce=Token;
            MinimumFrame=GFrameNumber;Frames.Reset();
        }

        void Disarm()
        {
            FScopeLock Lock(&Mutex);
            ExpectedScene=nullptr;ExpectedTarget=nullptr;Nonce.Reset();Frames.Reset();
        }

        TSharedPtr<FJsonObject> Find(const FString& Token, uint32 Frame)
        {
            FString Serialized;
            {
                FScopeLock Lock(&Mutex);
                if (Nonce!=Token) return nullptr;
                const auto* Found=Frames.Find(Frame);
                if (!Found) return nullptr;
                Serialized=*Found;
            }
            // JSON shared pointers remain on their creating thread; only bytes cross the lock.
            TSharedPtr<FJsonObject> Result;
            return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Serialized),Result) ? Result : nullptr;
        }

        TSharedPtr<FJsonObject> Latest(const FString& Token)
        {
            uint32 Last=0;
            {
                FScopeLock Lock(&Mutex);
                if (Nonce!=Token || Frames.IsEmpty()) return nullptr;
                for (const auto& Pair:Frames) Last=FMath::Max(Last,Pair.Key);
            }
            return Find(Token,Last);
        }

        virtual void PreRenderView_RenderThread(FRDGBuilder&, FSceneView& View) override
        {
            FScopeLock Lock(&Mutex);
            if (!ExpectedScene || Nonce.IsEmpty() || !View.Family
                || View.Family->Scene!=ExpectedScene || View.Family->RenderTarget!=ExpectedTarget
                || View.Family->FrameNumber<MinimumFrame || View.Family->Views.Num()!=1
                || View.bIsSceneCapture || View.bIsPlanarReflection || View.bIsReflectionCapture) return;
            if (Frames.Num()>=16) return;
            const auto& Settings=View.FinalPostProcessSettings;
            auto J=MakeShared<FJsonObject>();
            J->SetBoolField(TEXT("available"),true);
            J->SetStringField(TEXT("readThread"),TEXT("render"));
            J->SetStringField(TEXT("nonce"),Nonce);
            J->SetNumberField(TEXT("frameNumber"),View.Family->FrameNumber);
            J->SetNumberField(TEXT("viewCount"),View.Family->Views.Num());
            const FVector Origin=View.ViewMatrices.GetViewOrigin();
            J->SetArrayField(TEXT("viewOriginCm"),{MakeShared<FJsonValueNumber>(Origin.X),
                MakeShared<FJsonValueNumber>(Origin.Y),MakeShared<FJsonValueNumber>(Origin.Z)});
            J->SetArrayField(TEXT("unscaledViewRect"),{MakeShared<FJsonValueNumber>(View.UnscaledViewRect.Min.X),
                MakeShared<FJsonValueNumber>(View.UnscaledViewRect.Min.Y),
                MakeShared<FJsonValueNumber>(View.UnscaledViewRect.Max.X),MakeShared<FJsonValueNumber>(View.UnscaledViewRect.Max.Y)});
            J->SetBoolField(TEXT("captureBindingVerified"),false);
            J->SetBoolField(TEXT("diagnosticOnly"),true);
            J->SetBoolField(TEXT("rendererStateVerified"),false);
            J->SetBoolField(TEXT("lightingApproved"),false);
            J->SetStringField(TEXT("giMethod"),Settings.DynamicGlobalIlluminationMethod==EDynamicGlobalIlluminationMethod::Lumen ? TEXT("Lumen") : TEXT("Other"));
            J->SetStringField(TEXT("reflectionMethod"),Settings.ReflectionMethod==EReflectionMethod::Lumen ? TEXT("Lumen") : TEXT("Other"));
            J->SetNumberField(TEXT("giMethodEnum"),static_cast<int32>(Settings.DynamicGlobalIlluminationMethod));
            J->SetNumberField(TEXT("reflectionMethodEnum"),static_cast<int32>(Settings.ReflectionMethod));
            J->SetNumberField(TEXT("antiAliasingMethodEnum"),static_cast<int32>(View.AntiAliasingMethod));
            J->SetNumberField(TEXT("exposureMinimum"),Settings.AutoExposureMinBrightness);
            J->SetNumberField(TEXT("exposureMaximum"),Settings.AutoExposureMaxBrightness);
            J->SetNumberField(TEXT("exposureBias"),Settings.AutoExposureBias);
            J->SetNumberField(TEXT("featureLevel"),static_cast<int32>(View.GetFeatureLevel()));
            J->SetNumberField(TEXT("shaderPlatform"),static_cast<int32>(View.GetShaderPlatform()));
            J->SetStringField(TEXT("rhi"),GDynamicRHI ? GDynamicRHI->GetName() : TEXT("unavailable"));
            J->SetBoolField(TEXT("projectSupportsLumen"),DoesProjectSupportLumenGI(View.GetShaderPlatform()));
            J->SetBoolField(TEXT("platformSupportsLumen"),DoesPlatformSupportLumenGI(View.GetShaderPlatform(),false));
            J->SetBoolField(TEXT("projectSupportsDistanceFields"),DoesProjectSupportDistanceFields());
            J->SetBoolField(TEXT("viewStatePresent"),View.State!=nullptr);
            J->SetBoolField(TEXT("rayTracingEnabledForProject"),IsRayTracingEnabledForProject(View.GetShaderPlatform()));
            J->SetBoolField(TEXT("rayTracingEnabled"),IsRayTracingEnabled(View.GetShaderPlatform()));
            J->SetBoolField(TEXT("rayTracingAllowedForView"),View.IsRayTracingAllowedForView());
            J->SetBoolField(TEXT("supportsInlineRayTracing"),GRHISupportsInlineRayTracing);
            J->SetBoolField(TEXT("supportsRayTracingShaders"),GRHISupportsRayTracingShaders);
            J->SetBoolField(TEXT("supportsRayTracingDispatchIndirect"),GRHISupportsRayTracingDispatchIndirect);
            auto Flags=MakeShared<FJsonObject>();
            for (const TCHAR* Name:{TEXT("Lighting"),TEXT("GlobalIllumination"),TEXT("LumenGlobalIllumination"),
                TEXT("LumenReflections"),TEXT("LumenScreenTraces"),TEXT("LumenDetailTraces"),TEXT("LumenGlobalTraces"),TEXT("PathTracing"),TEXT("RayTracingDebug")})
            {
                const int32 Index=FEngineShowFlags::FindIndexByName(Name);
                if (Index>=0) Flags->SetBoolField(Name,View.Family->EngineShowFlags.GetSingleFlag(Index));
                else Flags->SetField(Name,MakeShared<FJsonValueNull>());
            }
            J->SetObjectField(TEXT("showFlags"),Flags);
            auto CVars=MakeShared<FJsonObject>();
            for (const TCHAR* Name:{TEXT("r.Lumen.Supported"),TEXT("r.ForwardShading"),TEXT("r.GenerateMeshDistanceFields"),
                TEXT("r.ScreenPercentage"),TEXT("r.DynamicRes.OperationMode"),TEXT("r.ShadowQuality"),
                TEXT("r.Shadow.CSM.MaxCascades"),TEXT("r.Shadow.MaxResolution"),TEXT("r.AntiAliasingMethod"),
                TEXT("r.TemporalAA.Quality"),TEXT("r.ViewDistanceScale"),
                TEXT("r.DistanceFields.SupportEvenIfHardwareRayTracingSupported"),TEXT("r.Lumen.DiffuseIndirect.Allow"),
                TEXT("r.Lumen.Reflections.Allow"),TEXT("r.Lumen.FinalGatherMethod"),TEXT("r.Lumen.HardwareRayTracing"),
                TEXT("r.Lumen.TraceMeshSDFs"),TEXT("r.Lumen.TraceMeshSDFs.Allow"),TEXT("r.RayTracing"),
                TEXT("r.Lumen.ScreenProbeGather.TraceMeshSDFs"),TEXT("r.Lumen.Reflections.TraceMeshSDFs"),
                TEXT("r.Lumen.ScreenProbeGather.HardwareRayTracing"),TEXT("r.Lumen.Reflections.HardwareRayTracing"),
                TEXT("r.Lumen.HardwareRayTracing.LightingMode"),TEXT("r.MeshCardRepresentation"),
                TEXT("r.SkinCache.CompileShaders"),TEXT("r.StaticMesh.StripDistanceFieldDataDuringLoad"),
                TEXT("r.Lumen.ScreenProbeGather.ScreenTraces"),TEXT("r.Lumen.Reflections.ScreenTraces")})
            {
                CVars->SetObjectField(Name,WarCitadelLumenViewProbe::ReadConsoleVariable(Name));
            }
            J->SetObjectField(TEXT("cvars"),CVars);
            J->SetField(TEXT("actualBackend"),MakeShared<FJsonValueNull>());
            FString Serialized;
            FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Serialized));
            Frames.Add(View.Family->FrameNumber,MoveTemp(Serialized));
        }

    private:
        FCriticalSection Mutex;
        const FSceneInterface* ExpectedScene=nullptr;
        const FRenderTarget* ExpectedTarget=nullptr;
        FString Nonce;
        uint32 MinimumFrame=0;
        TMap<uint32,FString> Frames;
    };
    TSharedPtr<FProbe,ESPMode::ThreadSafe> Probe;
    TWeakObjectPtr<UWorld> ProbeWorld;
}

TSharedPtr<FJsonObject> WarCitadelLumenViewProbe::ReadConsoleVariable(const TCHAR* Name)
{
    auto Row=MakeShared<FJsonObject>();
    const auto* Variable=IConsoleManager::Get().FindConsoleVariable(Name);
    Row->SetBoolField(TEXT("available"),Variable!=nullptr);
    if (Variable)
    {
        const auto Flags=Variable->GetFlags();
        // UE 5.8's generic getter uses the calling thread's shadow. Typed-data
        // lookup raises an ensure for Ref CVars; integer reads also truncate floats.
        Row->SetNumberField(TEXT("value"),Variable->GetFloat());
        Row->SetNumberField(TEXT("setByFlags"),static_cast<uint32>(Flags & ECVF_SetByMask));
        Row->SetNumberField(TEXT("flags"),static_cast<uint32>(Flags));
    }
    return Row;
}

bool WarCitadelLumenViewProbe::Arm(UWorld* World, const FRenderTarget* GameRenderTarget, const FString& Nonce)
{
    if (!IsInGameThread() || !World || !World->IsGameWorld() || !World->Scene || !GameRenderTarget || Nonce.IsEmpty()) return false;
    if (!Probe || ProbeWorld.Get()!=World)
    {
        if (Probe) Probe->Disarm();
        Probe=FSceneViewExtensions::NewExtension<FProbe>(World);ProbeWorld=World;
    }
    Probe->Arm(World->Scene,GameRenderTarget,Nonce);
    return true;
}

TSharedPtr<FJsonObject> WarCitadelLumenViewProbe::FindFrame(const FString& Nonce, uint32 ImageFrameNumber)
{
    if (!IsInGameThread() || !Probe) return nullptr;
    return Probe->Find(Nonce,ImageFrameNumber);
}

TSharedPtr<FJsonObject> WarCitadelLumenViewProbe::LatestUnbound(const FString& Nonce)
{
    if (!IsInGameThread() || !Probe) return nullptr;
    return Probe->Latest(Nonce);
}

void WarCitadelLumenViewProbe::Disarm()
{
    if (!IsInGameThread()) return;
    if (Probe) Probe->Disarm();
    Probe.Reset();ProbeWorld.Reset();
}
