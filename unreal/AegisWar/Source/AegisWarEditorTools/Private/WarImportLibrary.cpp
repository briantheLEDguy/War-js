#include "WarImportLibrary.h"
#include "Animation/AnimSequence.h"
#include "Factories/FbxAnimSequenceImportData.h"
#include "Modules/ModuleManager.h"
#include "Engine/StaticMesh.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "PhysicsEngine/BodySetup.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "GameFramework/Actor.h"
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#include "RenderingThread.h"
#include "Engine/World.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, AegisWarEditorTools);

UBoxComponent* UWarImportLibrary::SetCapitalBuildingCollision(AActor* Actor, const int32 Index,
    const FVector Center, const FVector HalfSize, const double YawDegrees)
{
    if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("WarCapitalBuilding")) || !Actor->GetRootComponent()
        || Index < 0 || Index > 255 || Center.ContainsNaN() || Center.GetAbsMax() > 100000000.0
        || HalfSize.ContainsNaN() || HalfSize.GetMin() <= 0 || HalfSize.GetMax() > 10000000.0
        || !FMath::IsFinite(YawDegrees)) return nullptr;
    const FName Name(*FString::Printf(TEXT("AuthoredCollision_%d"), Index));
    UBoxComponent* Box = FindObject<UBoxComponent>(Actor, *Name.ToString());
    if (Box && !Box->ComponentHasTag(TEXT("WarCapitalBuildingCollision"))) return nullptr;
    if (!Box)
    {
        if (FindObject<UObject>(Actor, *Name.ToString())) return nullptr;
        Box = NewObject<UBoxComponent>(Actor, Name, RF_Transactional);
        Box->ComponentTags.Add(TEXT("WarCapitalBuildingCollision"));
        Actor->AddInstanceComponent(Box);
        Box->SetMobility(Actor->GetRootComponent()->Mobility);
        Box->SetupAttachment(Actor->GetRootComponent());
        Box->RegisterComponent();
    }
    Box->SetWorldTransform(FTransform(FRotator(0, YawDegrees, 0), Center, FVector::OneVector));
    Box->SetBoxExtent(HalfSize);
    Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->SetGenerateOverlapEvents(false);
    Box->SetHiddenInGame(true);
    Box->SetVisibility(false);
    Actor->MarkPackageDirty();
    return Box;
}

UStaticMesh* UWarImportLibrary::CreateCapitalSurface(const FString& ZoneId, const FString& Surface,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, UMaterialInterface* Material, const bool bCollision)
{
    if (ZoneId != TEXT("aegis_capital") || (Surface != TEXT("ground") && Surface != TEXT("water") && Surface != TEXT("bed"))
        || !Material || Positions.IsEmpty() || Positions.Num() > 2000000 || Positions.Num() != Normals.Num()
        || Positions.Num() != UVs.Num() || Indices.IsEmpty() || Indices.Num() % 3 || Indices.Num() > 6000000
        || bCollision != (Surface != TEXT("water"))) return nullptr;
    for (int32 Index = 0; Index < Positions.Num(); ++Index)
    {
        if (Positions[Index].ContainsNaN() || Positions[Index].GetAbsMax() > 100000000.0
            || Normals[Index].ContainsNaN() || !Normals[Index].IsNormalized()
            || !FMath::IsFinite(UVs[Index].X) || !FMath::IsFinite(UVs[Index].Y)) return nullptr;
    }
    for (int32 Index : Indices) if (!Positions.IsValidIndex(Index)) return nullptr;
    for (int32 Index = 0; Index < Indices.Num(); Index += 3)
    {
        if (FVector::CrossProduct(Positions[Indices[Index + 1]] - Positions[Indices[Index]],
            Positions[Indices[Index + 2]] - Positions[Indices[Index]]).IsNearlyZero()) return nullptr;
    }
    const FString Owner = ZoneId + TEXT(":") + Surface;
    const FString Name = TEXT("Terrain_") + Surface;
    const FString PackageName = TEXT("/Game/Capitals/") + ZoneId + TEXT("/") + Name;
    UPackage* Package = CreatePackage(*PackageName);
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *(PackageName + TEXT(".") + Name));
    if (Mesh && Package->GetMetaData().GetValue(Mesh, TEXT("WarCapitalTerrain")) != Owner) return nullptr;
    const bool bCreated = !Mesh;
    if (!Mesh) Mesh = NewObject<UStaticMesh>(Package, *Name, RF_Public | RF_Standalone);
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description);
    Attributes.Register();
    auto VertexPositions = Attributes.GetVertexPositions();
    auto VertexNormals = Attributes.GetVertexInstanceNormals();
    auto Tangents = Attributes.GetVertexInstanceTangents();
    auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    auto Colors = Attributes.GetVertexInstanceColors();
    auto VertexUVs = Attributes.GetVertexInstanceUVs();
    VertexUVs.SetNumChannels(1);
    const FPolygonGroupID Group = Description.CreatePolygonGroup();
    Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Surface");
    TArray<FVertexID> Vertices;
    Vertices.Reserve(Positions.Num());
    for (const auto& Position : Positions)
    {
        const FVertexID Vertex = Description.CreateVertex();
        VertexPositions[Vertex] = FVector3f(Position);
        Vertices.Add(Vertex);
    }
    for (int32 Index = 0; Index < Indices.Num(); Index += 3)
    {
        TArray<FVertexInstanceID> Corners;
        for (int32 Offset = 0; Offset < 3; ++Offset)
        {
            const int32 Source = Indices[Index + Offset];
            const FVertexInstanceID Instance = Description.CreateVertexInstance(Vertices[Source]);
            VertexNormals[Instance] = FVector3f(Normals[Source]);
            FVector Tangent = FVector::VectorPlaneProject(FVector::YAxisVector, Normals[Source]).GetSafeNormal();
            if (Tangent.IsNearlyZero()) Tangent = FVector::VectorPlaneProject(FVector::XAxisVector, Normals[Source]).GetSafeNormal();
            Tangents[Instance] = FVector3f(Tangent);
            Signs[Instance] = 1.f;
            Colors[Instance] = FVector4f(1, 1, 1, 1);
            VertexUVs.Set(Instance, 0, FVector2f(UVs[Source]));
            Corners.Add(Instance);
        }
        Description.CreateTriangle(Group, Corners);
    }
    Mesh->GetStaticMaterials().Reset();
    Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, TEXT("Surface")));
    if (!Mesh->BuildFromMeshDescriptions({ &Description })) return nullptr;
    if (bCollision)
    {
        Mesh->CreateBodySetup();
        Mesh->GetBodySetup()->CollisionTraceFlag = CTF_UseComplexAsSimple;
        Mesh->GetBodySetup()->bDoubleSidedGeometry = true;
        Mesh->GetBodySetup()->InvalidatePhysicsData();
        Mesh->GetBodySetup()->CreatePhysicsMeshes();
    }
    Package->GetMetaData().SetValue(Mesh, TEXT("WarCapitalTerrain"), *Owner);
    if (bCreated) FAssetRegistryModule::AssetCreated(Mesh);
    Mesh->MarkPackageDirty();
    return Mesh;
}

FBox UWarImportLibrary::GetSkinnedBounds(USkeletalMeshComponent* Component)
{
    FBox Bounds(ForceInit);
    if (!Component) return Bounds;
    const FSkeletalMeshRenderData* RenderData = Component->GetSkeletalMeshRenderData();
    const FSkinWeightVertexBuffer* Weights = Component->GetSkinWeightBuffer(0);
    if (!RenderData || RenderData->LODRenderData.IsEmpty() || !Weights) return Bounds;
    TArray<FMatrix44f> Matrices;
    Component->GetCurrentRefToLocalMatrices(Matrices, 0);
    const auto& LOD = RenderData->LODRenderData[0];
    for (uint32 Index = 0; Index < LOD.GetNumVertices(); ++Index)
        Bounds += FVector(USkeletalMeshComponent::GetSkinnedVertexPosition(Component, Index, LOD, *Weights, Matrices));
    return Bounds;
}

void UWarImportLibrary::PreparePreviewFrame(USkeletalMeshComponent* Component)
{
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    if (Component)
    {
        Component->TickAnimation(0.f, false);
        Component->RefreshBoneTransforms();
        Component->UpdateComponentToWorld();
        Component->MarkRenderTransformDirty();
        if (UWorld* World = Component->GetWorld()) World->SendAllEndOfFrameUpdates();
    }
    FlushRenderingCommands();
}

FString UWarImportLibrary::GetSourceAnimationName(const UAnimSequence* Animation)
{
    const UFbxAnimSequenceImportData* Data = Animation
        ? Cast<UFbxAnimSequenceImportData>(Animation->AssetImportData) : nullptr;
    return Data ? Data->SourceAnimationName : FString();
}

UStaticMesh* UWarImportLibrary::CreateProofTerrain(UMaterialInterface* Material)
{
    if (!Material) return nullptr;
    const TCHAR* PackageName = TEXT("/Game/MigrationProof/Terrain");
    UPackage* Package = CreatePackage(PackageName);
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/MigrationProof/Terrain.Terrain"));
    if (Mesh && Package->GetMetaData().GetValue(Mesh, TEXT("WarMigrationProof")) != FString(TEXT("schema-1"))) return nullptr;
    if (!Mesh) Mesh = NewObject<UStaticMesh>(Package, TEXT("Terrain"), RF_Public | RF_Standalone);
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description);
    Attributes.Register();
    auto Positions = Attributes.GetVertexPositions();
    auto Normals = Attributes.GetVertexInstanceNormals();
    auto Tangents = Attributes.GetVertexInstanceTangents();
    auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    auto Colors = Attributes.GetVertexInstanceColors();
    auto UVs = Attributes.GetVertexInstanceUVs();
    UVs.SetNumChannels(1);
    const FPolygonGroupID Group = Description.CreatePolygonGroup();
    Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Ground");
    constexpr int32 Cells = 40;
    TArray<FVertexID> Vertices;
    for (int32 Y = 0; Y <= Cells; ++Y)
    {
        for (int32 X = 0; X <= Cells; ++X)
        {
            const FVertexID Vertex = Description.CreateVertex();
            Positions[Vertex] = FVector3f((X - Cells / 2) * 100.f, (Y - Cells / 2) * 100.f, 0.f);
            Vertices.Add(Vertex);
        }
    }
    for (int32 Y = 0; Y < Cells; ++Y)
    {
        for (int32 X = 0; X < Cells; ++X)
        {
            const int32 A = Y * (Cells + 1) + X;
            const int32 Indices[] = { A, A + Cells + 2, A + 1, A, A + Cells + 1, A + Cells + 2 };
            for (int32 Triangle = 0; Triangle < 2; ++Triangle)
            {
                TArray<FVertexInstanceID> Corners;
                for (int32 Corner = 0; Corner < 3; ++Corner)
                {
                    const FVertexID Vertex = Vertices[Indices[Triangle * 3 + Corner]];
                    const FVertexInstanceID Instance = Description.CreateVertexInstance(Vertex);
                    Normals[Instance] = FVector3f(0, 0, 1);
                    Tangents[Instance] = FVector3f(1, 0, 0);
                    Signs[Instance] = 1.f;
                    Colors[Instance] = FVector4f(1, 1, 1, 1);
                    UVs.Set(Instance, 0, FVector2f(Positions[Vertex].X / 400.f, Positions[Vertex].Y / 400.f));
                    Corners.Add(Instance);
                }
                Description.CreateTriangle(Group, Corners);
            }
        }
    }
    Mesh->GetStaticMaterials().Reset();
    Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, TEXT("Ground")));
    if (!Mesh->BuildFromMeshDescriptions({ &Description })) return nullptr;
    Mesh->CreateBodySetup();
    Mesh->GetBodySetup()->CollisionTraceFlag = CTF_UseComplexAsSimple;
    Mesh->GetBodySetup()->bDoubleSidedGeometry = true;
    Mesh->GetBodySetup()->InvalidatePhysicsData();
    Mesh->GetBodySetup()->CreatePhysicsMeshes();
    FAssetRegistryModule::AssetCreated(Mesh);
    Mesh->MarkPackageDirty();
    return Mesh;
}
