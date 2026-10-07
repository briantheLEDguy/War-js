#include "WarImportLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "Misc/PackageName.h"
#include "PhysicsEngine/BodySetup.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshResources.h"
#include "UObject/MetaData.h"
#include "UObject/Package.h"

namespace
{
    bool IsStudyCollection(const FString& Collection)
    {
        const FString Prefix = TEXT("AegisCitadel_");
        if (!Collection.StartsWith(Prefix) || Collection.Len() != Prefix.Len() + 12) return false;
        for (const TCHAR C : Collection.Mid(Prefix.Len()))
            if (!((C >= TEXT('0') && C <= TEXT('9')) || (C >= TEXT('a') && C <= TEXT('f')))) return false;
        return true;
    }

    UStaticMesh* CreateStudy(UStaticMesh* Source, const FString& Collection, const FString& Key,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector>& Tangents, const TArray<double>& Signs, const TArray<FVector2D>& UV0,
        const TArray<FVector2D>& UV1, const TArray<int32>& TriangleMaterials,
        const TArray<UMaterialInterface*>& Materials, bool bAutomation)
    {
        if (!IsInGameThread() || !IsValid(Source) || Materials.IsEmpty() || Materials.Num() > 4
            || Materials.Contains(nullptr) || !IsStudyCollection(Collection)
            || !(Key == TEXT("SM_PrivateHighland") || Key == TEXT("SM_PrivateBackdrop") || Key == TEXT("SM_PrivateApron"))) return nullptr;
        const FString SourcePath = Source->GetOutermost()->GetName();
        const FString SourceCollection = SourcePath.Mid(FString(TEXT("/Game/WorldRebuild/")).Len()).Left(25);
        if (!bAutomation && (!SourcePath.StartsWith(TEXT("/Game/WorldRebuild/"))
            || !IsStudyCollection(SourceCollection) || !SourcePath.EndsWith(TEXT("/Meshes/SM_HallCarvedMountain")))) return nullptr;
        if (bAutomation && Source->GetOutermost() != GetTransientPackage()) return nullptr;
        if (Source->GetNumSourceModels() != 1 || Source->GetStaticMaterials().Num() != 1
            || Source->GetNaniteSettings().bEnabled || Source->GetSourceModel(0).BuildSettings.BuildScale3D != FVector(1)
            || !Source->GetSourceModel(0).BuildSettings.bGenerateLightmapUVs
            || Source->GetSourceModel(0).BuildSettings.SrcLightmapIndex != 0
            || Source->GetSourceModel(0).BuildSettings.DstLightmapIndex != 1) return nullptr;
        const int32 Count = Positions.Num();
        if (Count < 3 || Count > 1500000 || Indices.IsEmpty() || Indices.Num() > 1500000 || Indices.Num() % 3
            || Normals.Num() != Count || Tangents.Num() != Count || Signs.Num() != Count
            || UV0.Num() != Count || UV1.Num() != Count || TriangleMaterials.Num() != Indices.Num() / 3) return nullptr;
        for (const auto* Material : Materials) if (!IsValid(Material)) return nullptr;
        for (const int32 Slot : TriangleMaterials) if (!Materials.IsValidIndex(Slot)) return nullptr;
        for (int32 I = 0; I < Count; ++I)
        {
            if (Positions[I].ContainsNaN() || Positions[I].GetAbsMax() > 100000000
                || Normals[I].ContainsNaN() || Tangents[I].ContainsNaN()
                || !Normals[I].IsNormalized() || !Tangents[I].IsNormalized()
                || FMath::Abs(FVector::DotProduct(Normals[I], Tangents[I])) > .002
                || !(Signs[I] == -1 || Signs[I] == 1)
                || !FMath::IsFinite(UV0[I].X) || !FMath::IsFinite(UV0[I].Y)
                || !FMath::IsFinite(UV1[I].X) || !FMath::IsFinite(UV1[I].Y)) return nullptr;
        }
        for (const int32 I : Indices) if (!Positions.IsValidIndex(I)) return nullptr;
        for (int32 I = 0; I < Indices.Num(); I += 3)
            if (FVector::CrossProduct(Positions[Indices[I+1]] - Positions[Indices[I]],
                Positions[Indices[I+2]] - Positions[Indices[I]]).IsNearlyZero(1e-10)) return nullptr;
        const FString PackageName = TEXT("/Game/WorldRebuild/") + Collection + TEXT("/Meshes/") + Key;
        // A failed or existing study is retained for inspection; this factory never overwrites one.
        if (!bAutomation && (FindPackage(nullptr, *PackageName) || FPackageName::DoesPackageExist(PackageName))) return nullptr;
        UPackage* Package = bAutomation ? GetTransientPackage() : CreatePackage(*PackageName);
        UStaticMesh* Mesh = NewObject<UStaticMesh>(Package, bAutomation ? NAME_None : FName(*Key),
            bAutomation ? RF_Transient : RF_Public | RF_Standalone);
        Mesh->AddSourceModel();
        auto& TargetSource = Mesh->GetSourceModel(0);
        TargetSource.BuildSettings = Source->GetSourceModel(0).BuildSettings;
        TargetSource.ReductionSettings = Source->GetSourceModel(0).ReductionSettings;
        // Packed source directions are normalized in the signed transport, and
        // derived corners carry an explicit UV tangent basis. Recomputing would
        // discard both and can invert this source's declared native normal side.
        TargetSource.BuildSettings.bRecomputeNormals = false;
        TargetSource.BuildSettings.bRecomputeTangents = false;
        // Refinement introduces UV/basis values between the old packed corners.
        // Half UVs and 8-bit tangents lose the strict saved-corner comparison.
        // Change precision on this owned render copy; leave source policy intact.
        TargetSource.BuildSettings.bUseHighPrecisionTangentBasis = true;
        TargetSource.BuildSettings.bUseFullPrecisionUVs = true;
        Mesh->SetNaniteSettings(Source->GetNaniteSettings());
        Mesh->SetLightMapCoordinateIndex(Source->GetLightMapCoordinateIndex());
        Mesh->SetLightMapResolution(Source->GetLightMapResolution());
        Mesh->SetAutoComputeLODScreenSize(Source->GetAutoComputeLODScreenSize());
        FMeshDescription Description;
        FStaticMeshAttributes Attributes(Description);
        Attributes.Register();
        auto VertexPositions = Attributes.GetVertexPositions();
        auto CornerNormals = Attributes.GetVertexInstanceNormals();
        auto CornerTangents = Attributes.GetVertexInstanceTangents();
        auto CornerSigns = Attributes.GetVertexInstanceBinormalSigns();
        auto CornerUVs = Attributes.GetVertexInstanceUVs();
        CornerUVs.SetNumChannels(2);
        TArray<FPolygonGroupID> Groups;
        for (int32 I = 0; I < Materials.Num(); ++I)
        {
            const FPolygonGroupID Group = Description.CreatePolygonGroup();
            const FName Slot = Materials.Num() == 1 ? Source->GetStaticMaterials()[0].MaterialSlotName
                : FName(*FString::Printf(TEXT("Study_%d"), I));
            Attributes.GetPolygonGroupMaterialSlotNames()[Group] = Slot;
            Groups.Add(Group);
            Mesh->GetStaticMaterials().Add(FStaticMaterial(Materials[I], Slot));
        }
        TArray<FVertexID> Vertices;
        Vertices.Reserve(Count);
        for (const FVector& Position : Positions)
        {
            const FVertexID Vertex = Description.CreateVertex();
            VertexPositions[Vertex] = FVector3f(Position);
            Vertices.Add(Vertex);
        }
        for (int32 I = 0; I < Indices.Num(); I += 3)
        {
            TArray<FVertexInstanceID> Corners;
            for (int32 C = 0; C < 3; ++C)
            {
                const int32 Input = Indices[I+C];
                const FVertexInstanceID Corner = Description.CreateVertexInstance(Vertices[Input]);
                CornerNormals[Corner] = FVector3f(Normals[Input]);
                CornerTangents[Corner] = FVector3f(Tangents[Input]);
                CornerSigns[Corner] = float(Signs[Input]);
                CornerUVs.Set(Corner, 0, FVector2f(UV0[Input]));
                CornerUVs.Set(Corner, 1, FVector2f(UV1[Input]));
                Attributes.GetVertexInstanceColors()[Corner] = FVector4f(1, 1, 1, 1);
                Corners.Add(Corner);
            }
            Description.CreateTriangle(Groups[TriangleMaterials[I / 3]], Corners);
        }
        Mesh->CreateMeshDescription(0, MoveTemp(Description));
        Mesh->CommitMeshDescription(0);
        TArray<FText> Errors;
        Mesh->Build(true, &Errors);
        if (!Errors.IsEmpty() || !Mesh->GetRenderData()) return nullptr;
        Mesh->CreateBodySetup();
        Mesh->GetBodySetup()->AggGeom.EmptyElements();
        Mesh->GetBodySetup()->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        Package->GetMetaData().SetValue(Mesh, TEXT("WarCapitalTerrain"), *(Collection + TEXT(":") + Key));
        Package->GetMetaData().SetValue(Mesh, TEXT("WarCitadelRenderPolicySource"), *Source->GetPathName());
        Package->GetMetaData().SetValue(Mesh, TEXT("WarCitadelRenderOnlyStudy"), TEXT("true"));
        if (!bAutomation) { FAssetRegistryModule::AssetCreated(Mesh); Mesh->MarkPackageDirty(); }
        return Mesh;
    }
}

UStaticMesh* UWarImportLibrary::CreatePrivateCitadelRenderSurface(UStaticMesh* Source, const FString& Collection,
    const FString& Key, const TArray<FVector>& Positions, const TArray<int32>& Indices,
    const TArray<FVector>& Normals, const TArray<FVector>& Tangents, const TArray<double>& Signs,
    const TArray<FVector2D>& UV0, const TArray<FVector2D>& UV1, const TArray<int32>& TriangleMaterials,
    const TArray<UMaterialInterface*>& Materials)
{ return CreateStudy(Source, Collection, Key, Positions, Indices, Normals, Tangents, Signs, UV0, UV1, TriangleMaterials, Materials, false); }
#if WITH_DEV_AUTOMATION_TESTS
UStaticMesh* UWarImportLibrary::CreatePrivateCitadelRenderSurfaceForAutomation(UStaticMesh* Source,
    const FString& Collection, const FString& Key, const TArray<FVector>& Positions, const TArray<int32>& Indices,
    const TArray<FVector>& Normals, const TArray<FVector>& Tangents, const TArray<double>& Signs,
    const TArray<FVector2D>& UV0, const TArray<FVector2D>& UV1, const TArray<int32>& TriangleMaterials,
    const TArray<UMaterialInterface*>& Materials)
{ return CreateStudy(Source, Collection, Key, Positions, Indices, Normals, Tangents, Signs, UV0, UV1, TriangleMaterials, Materials, true); }
#endif
