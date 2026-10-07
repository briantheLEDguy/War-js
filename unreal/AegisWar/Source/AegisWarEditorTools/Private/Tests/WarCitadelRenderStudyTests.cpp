#if WITH_DEV_AUTOMATION_TESTS
#include "WarImportLibrary.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "Misc/AutomationTest.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonSerializer.h"
#include "StaticMeshResources.h"
#include "UObject/Package.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelRenderStudyTest, "AegisWar.Foundation.CitadelRenderStudy",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelRenderStudyTest::RunTest(const FString& Parameters)
{
    auto* Source = NewObject<UStaticMesh>(GetTransientPackage());
    Source->AddSourceModel();
    auto& Build = Source->GetSourceModel(0).BuildSettings;
    Build.bGenerateLightmapUVs = true; Build.SrcLightmapIndex = 0; Build.DstLightmapIndex = 1;
    Build.bRecomputeNormals = true; Build.bRecomputeTangents = true;
    Build.bUseHighPrecisionTangentBasis = false; Build.bUseFullPrecisionUVs = false;
    auto* Material = UMaterial::GetDefaultMaterial(MD_Surface);
    Source->GetStaticMaterials().Add(FStaticMaterial(Material, FName(TEXT("Mountain"))));
    Source->CreateBodySetup(); Source->GetBodySetup()->CollisionTraceFlag = CTF_UseComplexAsSimple;
    const auto OriginalBuild = Build;
    const bool DirtyBefore = Source->GetOutermost()->IsDirty();
    TArray<FVector> Positions = {{0,0,0}, {100,0,0}, {0,100,0}};
    TArray<int32> Indices = {0,1,2};
    TArray<FVector> Normals = {{0,0,-1}, {0,0,-1}, {0,0,-1}};
    TArray<FVector> Tangents = {{1,0,0}, {1,0,0}, {1,0,0}};
    TArray<double> Signs = {-1,-1,-1};
    TArray<FVector2D> UV0 = {{0,0}, {1,0}, {0,1}}, UV1 = UV0;
    const auto Create = [&](const FString& Collection = TEXT("AegisCitadel_0123456789ab"),
                            const FString& Key = TEXT("SM_PrivateHighland"))
    {
        return UWarImportLibrary::CreatePrivateCitadelRenderSurfaceForAutomation(Source, Collection, Key,
            Positions, Indices, Normals, Tangents, Signs, UV0, UV1, {0}, {Material});
    };
    TestNull(TEXT("Canonical collection is rejected"), Create(TEXT("AegisCapital")));
    TestNull(TEXT("Uppercase revision is rejected"), Create(TEXT("AegisCitadel_0123456789AB")));
    TestNull(TEXT("Unrelated model key is rejected"), Create(TEXT("AegisCitadel_0123456789ab"), TEXT("Player")));
    UV1.Pop(); TestNull(TEXT("Incomplete second UV channel is rejected before allocation"), Create()); UV1 = UV0;
    Signs[0] = 0; TestNull(TEXT("Unknown binormal handedness is rejected"), Create()); Signs[0] = -1;
    Tangents[0] = FVector(0,0,-1); TestNull(TEXT("Nonorthogonal tangent is rejected"), Create()); Tangents[0] = FVector(1,0,0);
    Normals[0] *= .5; TestNull(TEXT("Unnormalized transport normal is rejected"), Create()); Normals[0] = FVector(0,0,-1);
    Indices[2] = 1; TestNull(TEXT("Degenerate geometry is rejected"), Create()); Indices[2] = 2;
    Indices[2] = 3; TestNull(TEXT("Out-of-range index is rejected"), Create()); Indices[2] = 2;
    TestNull(TEXT("Public entry cannot use an unowned transient policy source"),
        UWarImportLibrary::CreatePrivateCitadelRenderSurface(Source, TEXT("AegisCitadel_0123456789ab"),
            TEXT("SM_PrivateHighland"), Positions, Indices, Normals, Tangents, Signs, UV0, UV1, {0}, {Material}));
    UStaticMesh* Target = Create();
    if (!TestNotNull(TEXT("Exact native winding and explicit basis build a private surface"), Target)) return false;
    TestTrue(TEXT("New surface is a separate mesh"), Target != Source);
    TestFalse(TEXT("Supplied normals are retained through the build policy"), Target->GetSourceModel(0).BuildSettings.bRecomputeNormals);
    TestFalse(TEXT("Supplied tangent basis is retained through the build policy"), Target->GetSourceModel(0).BuildSettings.bRecomputeTangents);
    TestTrue(TEXT("New basis corners use high precision"), Target->GetSourceModel(0).BuildSettings.bUseHighPrecisionTangentBasis);
    TestTrue(TEXT("Refined authored UVs use full precision"), Target->GetSourceModel(0).BuildSettings.bUseFullPrecisionUVs);
    TestTrue(TEXT("Generated UV1 policy remains explicit"), Target->GetSourceModel(0).BuildSettings.bGenerateLightmapUVs);
    TestEqual(TEXT("UV atlas destination remains channel one"), Target->GetSourceModel(0).BuildSettings.DstLightmapIndex, 1);
    TestEqual(TEXT("Render-only mesh contains no simple collision"), Target->GetBodySetup()->AggGeom.GetElementCount(), 0);
    TestEqual(TEXT("Render-only mesh avoids triangle collision"), Target->GetBodySetup()->CollisionTraceFlag.GetValue(), CTF_UseSimpleAsComplex);
    const auto& LOD = Target->GetRenderData()->LODResources[0];
    TestEqual(TEXT("Two native UV channels survive"), LOD.VertexBuffers.StaticMeshVertexBuffer.GetNumTexCoords(), uint32(2));
    TestEqual(TEXT("Source-oriented triangle survives"), LOD.IndexBuffer.GetNumIndices(), uint32(3));
    for (uint32 I = 0; I < LOD.VertexBuffers.StaticMeshVertexBuffer.GetNumVertices(); ++I)
        TestTrue(TEXT("Saved normals retain the declared native negative side"), LOD.VertexBuffers.StaticMeshVertexBuffer.VertexTangentZ(I).Z < -.99f);
    TestEqual(TEXT("Source normal recompute policy is unchanged"), Build.bRecomputeNormals, OriginalBuild.bRecomputeNormals);
    TestEqual(TEXT("Source tangent recompute policy is unchanged"), Build.bRecomputeTangents, OriginalBuild.bRecomputeTangents);
    TestEqual(TEXT("Source tangent precision is unchanged"), Build.bUseHighPrecisionTangentBasis, OriginalBuild.bUseHighPrecisionTangentBasis);
    TestEqual(TEXT("Source UV precision is unchanged"), Build.bUseFullPrecisionUVs, OriginalBuild.bUseFullPrecisionUVs);
    TestEqual(TEXT("Source collision remains authoritative"), Source->GetBodySetup()->CollisionTraceFlag.GetValue(), CTF_UseComplexAsSimple);
    TestEqual(TEXT("Source package dirtiness is unchanged"), Source->GetOutermost()->IsDirty(), DirtyBefore);
    return true;
}
#endif
