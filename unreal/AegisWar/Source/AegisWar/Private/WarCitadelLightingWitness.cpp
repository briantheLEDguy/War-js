#include "WarCitadelLightingWitness.h"
#include "WarCharacter.h"
#include "WarZoneAnchor.h"
#include "WarZoneLightingSubsystem.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/LightComponent.h"
#include "Components/LocalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstance.h"
#include "MaterialShared.h"
#include "Materials/MaterialRenderProxy.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "NavigationSystem.h"
#include "UObject/UnrealType.h"

namespace
{
    TArray<TSharedPtr<FJsonValue>> Vector(FVector V)
    { return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; }
    TArray<TSharedPtr<FJsonValue>> Color(FLinearColor V)
    { return {MakeShared<FJsonValueNumber>(V.R),MakeShared<FJsonValueNumber>(V.G),MakeShared<FJsonValueNumber>(V.B),MakeShared<FJsonValueNumber>(V.A)}; }
    TSharedPtr<FJsonObject> Component(const USceneComponent* C)
    {
        auto J=MakeShared<FJsonObject>();
        J->SetStringField(TEXT("component"),C->GetPathName());
        J->SetStringField(TEXT("class"),C->GetClass()->GetName());
        J->SetBoolField(TEXT("visible"),C->IsVisible());
        J->SetBoolField(TEXT("hiddenInGame"),C->bHiddenInGame);
        J->SetBoolField(TEXT("actorHidden"),C->GetOwner()->IsHidden());
        J->SetBoolField(TEXT("registered"),C->IsRegistered());
        J->SetBoolField(TEXT("renderStateCreated"),C->IsRenderStateCreated());
        J->SetNumberField(TEXT("mobility"),static_cast<int32>(C->Mobility.GetValue()));
        J->SetArrayField(TEXT("positionCm"),Vector(C->GetComponentLocation()));
        const auto R=C->GetComponentRotation();J->SetArrayField(TEXT("rotationDegrees"),Vector(FVector(R.Pitch,R.Yaw,R.Roll)));
        return J;
    }
    TSharedPtr<FJsonObject> Exposure(const FPostProcessSettings& S)
    {
        auto J=MakeShared<FJsonObject>();
        J->SetNumberField(TEXT("method"),static_cast<int32>(S.AutoExposureMethod.GetValue()));
        J->SetBoolField(TEXT("methodOverride"),S.bOverride_AutoExposureMethod);
        J->SetNumberField(TEXT("minimum"),S.AutoExposureMinBrightness);J->SetBoolField(TEXT("minimumOverride"),S.bOverride_AutoExposureMinBrightness);
        J->SetNumberField(TEXT("maximum"),S.AutoExposureMaxBrightness);J->SetBoolField(TEXT("maximumOverride"),S.bOverride_AutoExposureMaxBrightness);
        J->SetNumberField(TEXT("bias"),S.AutoExposureBias);J->SetBoolField(TEXT("biasOverride"),S.bOverride_AutoExposureBias);
        J->SetNumberField(TEXT("bloom"),S.BloomIntensity);return J;
    }
}

TSharedPtr<FJsonObject> WarCitadelLightingWitness::CaptureBackdrop(const UStaticMeshComponent* C)
{
    auto Row=MakeShared<FJsonObject>();
    Row->SetBoolField(TEXT("available"),IsValid(C) && IsInGameThread());
    Row->SetBoolField(TEXT("visualApproved"),false);Row->SetBoolField(TEXT("rendererStateVerified"),false);
    if (!IsValid(C) || !IsInGameThread()) return Row;
    Row->SetStringField(TEXT("component"),C->GetPathName());
    Row->SetStringField(TEXT("mesh"),C->GetStaticMesh() ? C->GetStaticMesh()->GetPathName() : FString());
    Row->SetBoolField(TEXT("registered"),C->IsRegistered());
    Row->SetBoolField(TEXT("renderStateCreated"),C->IsRenderStateCreated());
    Row->SetBoolField(TEXT("visible"),C->IsVisible());Row->SetBoolField(TEXT("hiddenInGame"),C->bHiddenInGame);
    Row->SetBoolField(TEXT("actorHidden"),C->GetOwner() && C->GetOwner()->IsHidden());
    Row->SetArrayField(TEXT("positionCm"),Vector(C->GetComponentLocation()));
    Row->SetArrayField(TEXT("scale"),Vector(C->GetComponentScale()));
    const auto R=C->GetComponentRotation();Row->SetArrayField(TEXT("rotationDegrees"),Vector(FVector(R.Pitch,R.Yaw,R.Roll)));
    Row->SetNumberField(TEXT("collisionEnabled"),static_cast<int32>(C->GetCollisionEnabled()));
    Row->SetStringField(TEXT("collisionProfile"),C->GetCollisionProfileName().ToString());
    bool Matches=C->GetCollisionEnabled()==ECollisionEnabled::NoCollision && C->GetCollisionProfileName()==TEXT("NoCollision");
    auto Properties=MakeShared<FJsonObject>();
    const TPair<const TCHAR*,const TCHAR*> Fields[]={
        {TEXT("cast_shadow"),TEXT("CastShadow")},{TEXT("cast_dynamic_shadow"),TEXT("bCastDynamicShadow")},
        {TEXT("cast_static_shadow"),TEXT("bCastStaticShadow")},{TEXT("cast_volumetric_translucent_shadow"),TEXT("bCastVolumetricTranslucentShadow")},
        {TEXT("cast_contact_shadow"),TEXT("bCastContactShadow")},{TEXT("self_shadow_only"),TEXT("bSelfShadowOnly")},
        {TEXT("cast_far_shadow"),TEXT("bCastFarShadow")},{TEXT("cast_inset_shadow"),TEXT("bCastInsetShadow")},
        {TEXT("cast_cinematic_shadow"),TEXT("bCastCinematicShadow")},{TEXT("cast_hidden_shadow"),TEXT("bCastHiddenShadow")},
        {TEXT("cast_shadow_as_two_sided"),TEXT("bCastShadowAsTwoSided")},
        {TEXT("can_ever_affect_navigation"),TEXT("bCanEverAffectNavigation")},
        {TEXT("generate_overlap_events"),TEXT("bGenerateOverlapEvents")},
        {TEXT("affect_distance_field_lighting"),TEXT("bAffectDistanceFieldLighting")},
        {TEXT("affect_dynamic_indirect_lighting"),TEXT("bAffectDynamicIndirectLighting")},
        {TEXT("affect_indirect_lighting_while_hidden"),TEXT("bAffectIndirectLightingWhileHidden")},
        {TEXT("visible_in_ray_tracing"),TEXT("bVisibleInRayTracing")},
        {TEXT("use_default_collision"),TEXT("bUseDefaultCollision")}};
    for (const auto& Field:Fields)
    {
        if (const auto* Property=FindFProperty<FBoolProperty>(C->GetClass(),Field.Value))
        {
            const bool Value=Property->GetPropertyValue_InContainer(C);
            Properties->SetBoolField(Field.Key,Value);Matches &= !Value;
        }
        else { Properties->SetField(Field.Key,MakeShared<FJsonValueNull>());Matches=false; }
    }
    Row->SetObjectField(TEXT("properties"),Properties);Row->SetBoolField(TEXT("controlsMatch"),Matches);
    const auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(C->GetWorld());
    const bool OctreeAvailable=Nav && Nav->GetNavOctree();
    Row->SetBoolField(TEXT("navigationOctreeAvailable"),OctreeAvailable);
    if (OctreeAvailable)
    {
        const FNavigationElementHandle ComponentHandle(C),ActorHandle(C->GetOwner());
        Row->SetBoolField(TEXT("navigationOctreeContainsComponent"),Nav->GetNavOctreeIdForElement(ComponentHandle)!=nullptr);
        Row->SetBoolField(TEXT("navigationOctreeContainsActor"),Nav->GetNavOctreeIdForElement(ActorHandle)!=nullptr);
        Row->SetBoolField(TEXT("navigationUpdatePending"),Nav->HasPendingUpdateForElement(ComponentHandle)
            || Nav->HasPendingUpdateForElement(ActorHandle));
    }
    return Row;
}

bool WarCitadelLightingWitness::PrivateSurfaceMaterialPath(const FString& Path)
{
    if (Path.Contains(TEXT("/M_PrivateSurface_"))) return true;
    FString Suffix;
    for (const TCHAR* Candidate:{
        TEXT("/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain"),
        TEXT("/Materials/M_DistantCrag_rock.M_DistantCrag_rock"),
        TEXT("/Materials/M_DistantCrag_dark_seam.M_DistantCrag_dark_seam"),
        TEXT("/Materials/M_DistantCrag_snow.M_DistantCrag_snow")})
        if (Path.EndsWith(Candidate)) { Suffix=Candidate;break; }
    if (Suffix.IsEmpty()) return false;
    const FString Prefix=TEXT("/Game/WorldRebuild/AegisCitadel_");
    const FString Root=Path.LeftChop(Suffix.Len());
    if (!Root.StartsWith(Prefix) || Root.Len()!=Prefix.Len()+12) return false;
    for (int32 I=Prefix.Len();I<Root.Len();++I)
        if (!((Root[I]>=TEXT('0') && Root[I]<=TEXT('9')) || (Root[I]>=TEXT('a') && Root[I]<=TEXT('f')))) return false;
    return true;
}

TArray<TSharedPtr<FJsonObject>> WarCitadelLightingWitness::CapturePrivateSurfaceMaterials(const UStaticMeshComponent* C)
{
    TArray<TSharedPtr<FJsonObject>> Rows;
    if (!IsValid(C) || !IsInGameThread() || !IsValid(C->GetOwner())) return Rows;
    const UStaticMesh* Mesh=C->GetStaticMesh();
    const FStaticMeshRenderData* Data=Mesh?Mesh->GetRenderData():nullptr;
    struct FProxyRead { const FMaterialRenderProxy* Proxy;TSharedPtr<FJsonObject> Json; };
    TArray<FProxyRead> Pending;
    const bool RendererAvailable=C->GetWorld() && C->GetWorld()->Scene;
    for (int32 Slot=0;Slot<C->GetNumMaterials();++Slot)
    {
        UMaterialInterface* Material=C->GetMaterial(Slot);
        if (!Material || !PrivateSurfaceMaterialPath(Material->GetPathName())) continue;
        auto Row=Component(C);Row->SetNumberField(TEXT("materialSlot"),Slot);
        Row->SetStringField(TEXT("material"),Material->GetPathName());
        const auto* Instance=Cast<UMaterialInstance>(Material);
        const auto* Base=Instance?Cast<UMaterial>(Instance->Parent.Get()):Material->GetMaterial();
        const auto* Proxy=Material->GetRenderProxy();const auto* ProxyInterface=Proxy?Proxy->GetMaterialInterface():nullptr;
        Row->SetStringField(TEXT("baseMaterial"),Base?Base->GetPathName():FString());
        Row->SetStringField(TEXT("proxyInterface"),ProxyInterface?ProxyInterface->GetPathName():FString());
        Row->SetBoolField(TEXT("hasStaticPermutationResource"),Instance && Instance->bHasStaticPermutationResource);
        Row->SetStringField(TEXT("mesh"),Mesh?Mesh->GetPathName():FString());
        Row->SetBoolField(TEXT("renderBuffersAvailable"),Data!=nullptr);
        Row->SetBoolField(TEXT("rendererAvailable"),RendererAvailable);
        Row->SetBoolField(TEXT("submittedMeshBatchVerified"),false);
        Row->SetBoolField(TEXT("screenshotPixelBindingVerified"),false);
        Row->SetBoolField(TEXT("visualApproved"),false);
        TArray<TSharedPtr<FJsonValue>> Sections;
        if (Data) for (int32 Lod=0;Lod<Data->LODResources.Num();++Lod)
            for (const auto& Section:Data->LODResources[Lod].Sections)
                if (Section.MaterialIndex==Slot && Section.NumTriangles)
                {
                    auto Entry=MakeShared<FJsonObject>();Entry->SetNumberField(TEXT("lod"),Lod);
                    Entry->SetNumberField(TEXT("triangles"),Section.NumTriangles);
                    Sections.Add(MakeShared<FJsonValueObject>(Entry));
                }
        Row->SetArrayField(TEXT("renderSections"),Sections);
        auto Resource=MakeShared<FJsonObject>();Resource->SetBoolField(TEXT("available"),false);
        Row->SetObjectField(TEXT("renderMaterial"),Resource);
        const FString ExpectedMountain=Material->GetPathName().Replace(TEXT("MI_PrivateSurface_mountain"),TEXT("M_PrivateSurface_mountain"));
        if (RendererAvailable && Proxy && Base && ProxyInterface==Material
            && (!Instance || (!Instance->bHasStaticPermutationResource && Base->GetPathName()==ExpectedMountain)))
            Pending.Add({Proxy,Resource});
        Rows.Add(Row);
    }
    if (!Pending.IsEmpty())
    {
        const auto Feature=C->GetWorld()->Scene->GetFeatureLevel();
        ENQUEUE_RENDER_COMMAND(WarReadCitadelSurfaceMaterials)([Pending=MoveTemp(Pending),Feature](FRHICommandListImmediate&)
        {
            for (const auto& Read:Pending)
            {
                const FMaterialRenderProxy* Fallback=nullptr;
                const FMaterial& Effective=Read.Proxy->GetMaterialWithFallback(Feature,Fallback);
                const FMaterialShaderMap* ShaderMap=Effective.GetRenderingThreadShaderMap();
                const UMaterialInterface* Owner=Effective.GetMaterialInterface();
                Read.Json->SetBoolField(TEXT("available"),true);
                Read.Json->SetBoolField(TEXT("usedFallback"),Fallback!=nullptr);
                Read.Json->SetStringField(TEXT("effectiveName"),Effective.GetFriendlyName());
                Read.Json->SetStringField(TEXT("effectiveInterface"),Owner?Owner->GetPathName():FString());
                Read.Json->SetNumberField(TEXT("materialDomain"),static_cast<int32>(Effective.GetMaterialDomain()));
                Read.Json->SetBoolField(TEXT("shaderMapPresent"),ShaderMap!=nullptr);
                Read.Json->SetBoolField(TEXT("shaderMapValidForRendering"),ShaderMap && ShaderMap->IsValidForRendering());
                if (ShaderMap) Read.Json->SetStringField(TEXT("baseMaterialId"),ShaderMap->GetShaderMapId().BaseMaterialId.ToString());
            }
        });
        FlushRenderingCommands();
    }
    return Rows;
}

bool WarCitadelLightingWitness::PrivateMaterialResourceReady(bool ExpectedInterface,bool UsedFallback,bool ShaderMapValid)
{
    return ExpectedInterface && !UsedFallback && ShaderMapValid;
}

TSharedPtr<FJsonObject> WarCitadelLightingWitness::PrivateMaterialReadiness(UWorld* World)
{
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("schemaVersion"),1);
    Report->SetBoolField(TEXT("readOnly"),true);Report->SetBoolField(TEXT("ready"),false);
    const bool Available=IsValid(World) && IsInGameThread() && World->Scene;
    Report->SetBoolField(TEXT("available"),Available);
    if (!Available) return Report;
    TSet<UMaterialInterface*> Materials;bool BuffersReady=true;
    for (TActorIterator<AActor> Actor(World);Actor;++Actor)
    {
        if (Actor->IsHidden()) continue;
        TInlineComponentArray<UStaticMeshComponent*> Components;Actor->GetComponents(Components);
        for (const auto* C:Components)
        {
            if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame) continue;
            const UStaticMesh* Mesh=C->GetStaticMesh();const auto* Data=Mesh?Mesh->GetRenderData():nullptr;
            for (int32 Slot=0;Slot<C->GetNumMaterials();++Slot)
            {
                auto* Material=C->GetMaterial(Slot);
                if (!Material || !PrivateSurfaceMaterialPath(Material->GetPathName())) continue;
                if (!Data) { BuffersReady=false;continue; }
                bool Used=false;
                for (const auto& Lod:Data->LODResources) for (const auto& Section:Lod.Sections)
                    Used |= Section.MaterialIndex==Slot && Section.NumTriangles>0;
                if (Used) Materials.Add(Material);
            }
        }
    }
    struct FRequest { const FMaterialRenderProxy* Proxy;const UMaterialInterface* Expected; };
    TArray<FRequest> Requests;
    for (auto* Material:Materials)
    {
        const auto* Instance=Cast<UMaterialInstance>(Material);
        const auto* Proxy=Material->GetRenderProxy();
        const UMaterialInterface* Expected=Instance?Cast<UMaterial>(Instance->Parent.Get()):Material->GetMaterial();
        // Non-static MI uniforms come from its proxy; the direct copied parent owns the shader resource.
        const FString ExpectedMountain=Material->GetPathName().Replace(TEXT("MI_PrivateSurface_mountain"),TEXT("M_PrivateSurface_mountain"));
        if (!Proxy || !Expected || Proxy->GetMaterialInterface()!=Material
            || (Instance && (Instance->bHasStaticPermutationResource || Expected->GetPathName()!=ExpectedMountain)))
        { BuffersReady=false;continue; }
        Requests.Add({Proxy,Expected});
    }
    auto Ready=MakeShared<int32>(0);const auto Feature=World->Scene->GetFeatureLevel();
    if (!Requests.IsEmpty())
    {
        ENQUEUE_RENDER_COMMAND(WarCheckCitadelMaterialReadiness)([Requests=MoveTemp(Requests),Ready,Feature](FRHICommandListImmediate&)
        {
            for (const auto& Request:Requests)
            {
                const FMaterialRenderProxy* Fallback=nullptr;
                const FMaterial& Effective=Request.Proxy->GetMaterialWithFallback(Feature,Fallback);
                const auto* ShaderMap=Effective.GetRenderingThreadShaderMap();
                if (PrivateMaterialResourceReady(Effective.GetMaterialInterface()==Request.Expected,Fallback!=nullptr,
                    ShaderMap && ShaderMap->IsValidForRendering())) ++*Ready;
            }
        });FlushRenderingCommands();
    }
    Report->SetNumberField(TEXT("materialCount"),Materials.Num());
    Report->SetNumberField(TEXT("readyMaterialCount"),*Ready);
    Report->SetBoolField(TEXT("renderBuffersReady"),BuffersReady);
    Report->SetBoolField(TEXT("ready"),BuffersReady && *Ready==Materials.Num());
    Report->SetBoolField(TEXT("submittedMeshBatchVerified"),false);
    Report->SetBoolField(TEXT("screenshotPixelBindingVerified"),false);
    return Report;
}

TSharedPtr<FJsonObject> WarCitadelLightingWitness::Capture(UWorld* World,const AWarCharacter* Pawn,const AActor* Camera)
{
    auto J=MakeShared<FJsonObject>();J->SetNumberField(TEXT("schemaVersion"),1);
    J->SetBoolField(TEXT("diagnosticOnly"),true);J->SetBoolField(TEXT("rendererStateVerified"),false);
    J->SetBoolField(TEXT("lightingApproved"),false);
    J->SetBoolField(TEXT("available"),World && IsInGameThread());
    if (!World || !IsInGameThread()) return J;
    J->SetStringField(TEXT("map"),World->GetOutermost()->GetName());
    J->SetNumberField(TEXT("worldSeconds"),World->GetTimeSeconds());
    J->SetBoolField(TEXT("viewportAvailable"),World->GetGameViewport()!=nullptr);
    if (const auto* V=World->GetGameViewport())
    {
        J->SetBoolField(TEXT("showAtmosphere"),V->EngineShowFlags.Atmosphere);
        J->SetBoolField(TEXT("showCloud"),V->EngineShowFlags.Cloud);
        J->SetBoolField(TEXT("showFog"),V->EngineShowFlags.Fog);
        J->SetBoolField(TEXT("showLighting"),V->EngineShowFlags.Lighting);
    }
    auto CVars=MakeShared<FJsonObject>();
    for (const TCHAR* Name:{TEXT("r.VolumetricCloud.Support"),TEXT("r.VolumetricCloud"),TEXT("r.VolumetricCloud.ViewRaySampleCountMax"),TEXT("r.Fog"),TEXT("r.VolumetricFog"),TEXT("r.EyeAdaptationQuality"),TEXT("r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange")})
        if (const auto* C=IConsoleManager::Get().FindConsoleVariable(Name)) CVars->SetNumberField(Name,C->GetFloat());
    J->SetObjectField(TEXT("consoleVariables"),CVars);
    if (Camera) J->SetArrayField(TEXT("cameraPositionCm"),Vector(Camera->GetActorLocation()));
    TArray<TSharedPtr<FJsonValue>> Zones,Clouds,Lights,Fogs,Post,Atmospheres,Backdrops,Surfaces;
    if (Pawn)
    {
        J->SetArrayField(TEXT("pawnPositionCm"),Vector(Pawn->GetActorLocation()));
        const auto* Zone=AWarZoneAnchor::FindAt(World,Pawn->GetActorLocation());
        J->SetStringField(TEXT("resolvedPawnZone"),Zone ? Zone->ZoneId.ToString() : FString());
        for (TActorIterator<AWarZoneAnchor> It(World);It;++It)
            if (AWarZoneAnchor::ContainsPoint(It->ZoneOrigin,It->HalfSize,Pawn->GetActorLocation()))
            {
                auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("actor"),It->GetPathName());
                Row->SetStringField(TEXT("zone"),It->ZoneId.ToString());Zones.Add(MakeShared<FJsonValueObject>(Row));
            }
    }
    if (const auto* S=World->GetSubsystem<UWarZoneLightingSubsystem>())
    {
        J->SetStringField(TEXT("activeLightingZone"),S->GetActiveZone().ToString());
        if (const auto* P=UWarZoneLightingSubsystem::FindProfile(S->GetActiveZone()))
        { J->SetBoolField(TEXT("authoredCapitalProfile"),P->bAuthoredCapital);J->SetStringField(TEXT("profileTheme"),P->Theme); }
    }
    for (TActorIterator<AActor> It(World);It;++It)
    {
        TInlineComponentArray<USceneComponent*> Components;It->GetComponents(Components);
        for (const auto* C:Components)
        {
            if (const auto* Mesh=Cast<UStaticMeshComponent>(C))
                for (const auto& Row:CapturePrivateSurfaceMaterials(Mesh))
                    Surfaces.Add(MakeShared<FJsonValueObject>(Row));
            if (It->ActorHasTag(TEXT("WarCitadelPrivateBackdrop")))
                if (const auto* Mesh=Cast<UStaticMeshComponent>(C))
                    Backdrops.Add(MakeShared<FJsonValueObject>(CaptureBackdrop(Mesh)));
            if (const auto* Cloud=Cast<UVolumetricCloudComponent>(C))
            {
                auto Row=Component(C);auto* Material=Cloud->GetMaterial();
                Row->SetStringField(TEXT("softMaterial"),Cloud->Material.ToSoftObjectPath().ToString());
                Row->SetStringField(TEXT("effectiveMaterial"),Material ? Material->GetPathName() : FString());
                const auto* Base=Material ? Material->GetMaterial() : nullptr;
                Row->SetStringField(TEXT("baseMaterial"),Base ? Base->GetPathName() : FString());
                Row->SetBoolField(TEXT("volumeDomain"),Base && Base->MaterialDomain==MD_Volume);
                // This diagnoses the effective render resource independently of
                // the UObject domain. It does not certify visible cloud pixels.
                if (Material && World->Scene)
                {
                    auto Resource=MakeShared<FJsonObject>();
                    auto* Proxy=Material->GetRenderProxy();const auto Feature=World->Scene->GetFeatureLevel();
                    ENQUEUE_RENDER_COMMAND(WarReadCloudMaterial)([Proxy,Feature,Resource](FRHICommandListImmediate&)
                    {
                        const FMaterialRenderProxy* Fallback=nullptr;
                        const FMaterial& Effective=Proxy->GetMaterialWithFallback(Feature,Fallback);
                        const auto* ShaderMap=Effective.GetRenderingThreadShaderMap();
                        Resource->SetBoolField(TEXT("usedFallback"),Fallback!=nullptr);
                        Resource->SetStringField(TEXT("effectiveName"),Effective.GetFriendlyName());
                        Resource->SetBoolField(TEXT("volumeDomain"),Effective.GetMaterialDomain()==MD_Volume);
                        Resource->SetBoolField(TEXT("shaderMapPresent"),ShaderMap!=nullptr);
                        Resource->SetBoolField(TEXT("shaderMapValidForRendering"),ShaderMap && ShaderMap->IsValidForRendering());
                    });
                    FlushRenderingCommands();Row->SetObjectField(TEXT("renderMaterial"),Resource);
                }
                if (const auto* Instance=Cast<UMaterialInstance>(Material))
                    Row->SetStringField(TEXT("parentMaterial"),Instance->Parent ? Instance->Parent->GetPathName() : FString());
                auto Scalars=MakeShared<FJsonObject>(),Vectors=MakeShared<FJsonObject>();
                if (Material)
                {
                    for (const TCHAR* Name:{TEXT("Layout_CloudGlobalScale"),TEXT("Cloud_GlobalCoverage"),TEXT("Cloud_GlobalDensity"),TEXT("StormClouds")})
                    { float Value=0;if (Material->GetScalarParameterValue(FHashedMaterialParameterInfo(Name),Value)) Scalars->SetNumberField(Name,Value); }
                    for (const TCHAR* Name:{TEXT("Layout_CloudType"),TEXT("Layout_CloudTypeMask"),TEXT("Layout_CloudPerTypeScale"),TEXT("Layout_GlobalTexturePlacement"),TEXT("Cloud_AlbedoColor"),TEXT("Storm_AlbedoColor"),TEXT("Layout_WindControls")})
                    { FLinearColor Value;if (Material->GetVectorParameterValue(FHashedMaterialParameterInfo(Name),Value)) Vectors->SetArrayField(Name,Color(Value)); }
                }
                Row->SetObjectField(TEXT("scalarParameters"),Scalars);Row->SetObjectField(TEXT("vectorParameters"),Vectors);
                Row->SetNumberField(TEXT("layerBottomKm"),Cloud->LayerBottomAltitude);Row->SetNumberField(TEXT("layerHeightKm"),Cloud->LayerHeight);
                Row->SetNumberField(TEXT("tracingStartDistanceKm"),Cloud->TracingStartDistanceFromCamera);
                Row->SetNumberField(TEXT("tracingStartMaxDistanceKm"),Cloud->TracingStartMaxDistance);
                Row->SetNumberField(TEXT("tracingMaxDistanceKm"),Cloud->TracingMaxDistance);
                Row->SetBoolField(TEXT("renderInMainPass"),Cloud->bRenderInMainPass);Row->SetBoolField(TEXT("holdout"),Cloud->bHoldout);
                Clouds.Add(MakeShared<FJsonValueObject>(Row));
            }
            else if (const auto* Atmosphere=Cast<USkyAtmosphereComponent>(C))
            {
                auto Row=Component(C);Row->SetNumberField(TEXT("transformMode"),static_cast<int32>(Atmosphere->TransformMode));
                Row->SetNumberField(TEXT("bottomRadiusKm"),Atmosphere->BottomRadius);
                Row->SetNumberField(TEXT("heightKm"),Atmosphere->AtmosphereHeight);
                Row->SetNumberField(TEXT("rayleighScale"),Atmosphere->RayleighScatteringScale);
                Row->SetNumberField(TEXT("rayleighDistributionKm"),Atmosphere->RayleighExponentialDistribution);
                Atmospheres.Add(MakeShared<FJsonValueObject>(Row));
            }
            else if (const auto* Light=Cast<ULightComponentBase>(C))
            {
                auto Row=Component(C);Row->SetNumberField(TEXT("intensity"),Light->Intensity);
                Row->SetArrayField(TEXT("color"),Color(Light->GetLightColor()));Row->SetBoolField(TEXT("castShadows"),Light->CastShadows);
                if (const auto* Local=Cast<ULocalLightComponent>(C))
                { Row->SetNumberField(TEXT("attenuationRadiusCm"),Local->AttenuationRadius);Row->SetNumberField(TEXT("intensityUnits"),static_cast<int32>(Local->IntensityUnits)); }
                if (const auto* L=Cast<ULightComponent>(C))
                { Row->SetNumberField(TEXT("temperatureK"),L->Temperature);Row->SetBoolField(TEXT("useTemperature"),L->bUseTemperature); }
                Lights.Add(MakeShared<FJsonValueObject>(Row));
            }
            else if (const auto* Fog=Cast<UExponentialHeightFogComponent>(C))
            {
                auto Row=Component(C);Row->SetNumberField(TEXT("density"),Fog->FogDensity);
                Row->SetNumberField(TEXT("startDistanceCm"),Fog->StartDistance);Row->SetNumberField(TEXT("maxOpacity"),Fog->FogMaxOpacity);
                Row->SetBoolField(TEXT("volumetric"),Fog->bEnableVolumetricFog);Fogs.Add(MakeShared<FJsonValueObject>(Row));
            }
            else if (const auto* P=Cast<UPostProcessComponent>(C))
            {
                auto Row=Component(C);Row->SetBoolField(TEXT("enabled"),P->bEnabled);Row->SetBoolField(TEXT("unbound"),P->bUnbound);
                Row->SetNumberField(TEXT("priority"),P->Priority);Row->SetNumberField(TEXT("weight"),P->BlendWeight);
                Row->SetObjectField(TEXT("exposure"),Exposure(P->Settings));Post.Add(MakeShared<FJsonValueObject>(Row));
            }
        }
        if (const auto* P=Cast<APostProcessVolume>(*It))
        {
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("actor"),P->GetPathName());Row->SetBoolField(TEXT("enabled"),P->bEnabled);
            Row->SetBoolField(TEXT("unbound"),P->bUnbound);Row->SetNumberField(TEXT("priority"),P->Priority);Row->SetNumberField(TEXT("weight"),P->BlendWeight);
            Row->SetObjectField(TEXT("exposure"),Exposure(P->Settings));Post.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    J->SetArrayField(TEXT("matchingPawnAnchors"),Zones);J->SetArrayField(TEXT("clouds"),Clouds);
    J->SetArrayField(TEXT("atmospheres"),Atmospheres);
    J->SetArrayField(TEXT("privateBackdrops"),Backdrops);
    J->SetArrayField(TEXT("privateSurfaceMaterials"),Surfaces);
    J->SetArrayField(TEXT("lights"),Lights);J->SetArrayField(TEXT("fogs"),Fogs);J->SetArrayField(TEXT("postProcesses"),Post);
    return J;
}
