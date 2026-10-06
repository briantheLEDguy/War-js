#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarImportLibrary.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "StaticMeshResources.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "PhysicsEngine/BodySetup.h"
#include "Interfaces/Interface_CollisionDataProvider.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Misc/PackageName.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarCitadelSiegeProof.h"
#include <initializer_list>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelTerrainCloneTest, "AegisWar.Foundation.CitadelTerrainClone",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCitadelTerrainCloneTest::RunTest(const FString& Parameters)
{
    auto* Material = UMaterial::GetDefaultMaterial(MD_Surface);
    auto* Source = UWarImportLibrary::CreateCompositeWorldSurface(TEXT("CitadelCarveAutomation"),
        TEXT("Source_") + FGuid::NewGuid().ToString(EGuidFormats::Digits),
        {{0,0,0},{100,0,0},{0,100,0},{0,0,0},{0,100,0},{0,0,100},
         {900,0,6000},{1020,0,6000},{900,120,6000}}, {0,2,1,0,5,2,6,8,7},
        {{0,0,1},{0,0,1},{0,0,1},{1,0,0},{1,0,0},{1,0,0},{0,0,1},{0,0,1},{0,0,1}},
        {{0,0},{1,0},{0,1},{.25,.25},{.5,.75},{1,.5},{0,0},{1,0},{0,1}},
        {FLinearColor(.1f,.2f,.3f,.4f),FLinearColor(.2f,.3f,.4f,.5f),FLinearColor(.3f,.4f,.5f,.6f),
         FLinearColor(.4f,.5f,.6f,.7f),FLinearColor(.5f,.6f,.7f,.8f),FLinearColor(.6f,.7f,.8f,.9f),
         FLinearColor(.25f,.5f,.75f,1),FLinearColor(.5f,.75f,1,.25f),FLinearColor(.75f,1,.25f,.5f)},
        {1,0,1}, {Material,Material}, true);
    if (!TestNotNull(TEXT("Actual unsaved multi-material source fixture is built"),Source)) return false;
    Source->SetFlags(RF_Transient);
    auto* Working = Source->GetMeshDescription(0);
    if (!TestNotNull(TEXT("Fixture has editable native source corners"),Working)) return false;
    FStaticMeshAttributes Attributes(*Working);
    auto UVs = Attributes.GetVertexInstanceUVs(); UVs.SetNumChannels(2);
    for (const FVertexInstanceID Corner : Working->VertexInstances().GetElementIDs())
    {
        UVs.Set(Corner,1,FVector2f(Corner.GetValue()*.125f,1.f-Corner.GetValue()*.125f));
        Attributes.GetVertexInstanceBinormalSigns()[Corner] = Corner.GetValue()<6 ? (Corner.GetValue()%2 ? -1.f : 1.f) : 0.f;
        if (Corner.GetValue()>=6) Attributes.GetVertexInstanceTangents()[Corner]=FVector3f::ZeroVector;
    }
    const FVertexID Orphan=Working->CreateVertex();Attributes.GetVertexPositions()[Orphan]=FVector3f(77,88,99);
    const FEdgeID OriginalCutEdge=Working->GetVertexPairEdge(FVertexID(6),FVertexID(7));
    Attributes.GetEdgeHardnesses()[OriginalCutEdge]=true;
    UStaticMesh::FCommitMeshDescriptionParams Commit; Commit.bMarkPackageDirty=false;
    Source->CommitMeshDescription(0,Commit);
    // Recomputed render tangents do not replace registered defaults in committed source attributes.
    Source->GetSourceModel(0).BuildSettings.bRecomputeTangents=true;
    Source->GetSourceModel(0).BuildSettings.bRecomputeNormals=true;
    Source->SetNumSourceModels(3);
    for (int32 Lod=1;Lod<3;++Lod)
    {
        Source->GetSourceModel(Lod).BuildSettings=Source->GetSourceModel(0).BuildSettings;
        Source->GetSourceModel(Lod).ReductionSettings.PercentTriangles=Lod==1?.65f:.3f;
    }
    Source->Build(true);
    UWarImportLibrary::DescribeStaticMeshRenderData(Source);
    Working=Source->GetMeshDescription(0);
    if (!TestNotNull(TEXT("Recomputed fixture retains a native working description"),Working)) return false;
    Source->GetOutermost()->SetDirtyFlag(false);
    auto* OriginalBody = Source->GetBodySetup();
    if (!TestNotNull(TEXT("Collision-enabled source has native BodySetup"),OriginalBody)) return false;
    OriginalBody->bDoubleSidedGeometry = true;
    const FString Raw = UWarImportLibrary::DescribeStaticMeshSourceData(Source);
    const FString OriginalTopology=UWarImportLibrary::DescribeStaticMeshStoredCorners(Source);
    const FString OriginalRendered=UWarImportLibrary::DescribeStaticMeshRenderedFaces(Source);
    TSharedPtr<FJsonObject> Export;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Export)) return false;
    FString RawHash,HashError;
    if (!TestTrue(TEXT("Actual source payload has an engine SHA-256"),WarCitadelProofHash::Text(Raw,RawHash,HashError))) return false;
    const auto Number=[](double Value)->TSharedPtr<FJsonValue> { return MakeShared<FJsonValueNumber>(Value); };
    const auto Vector=[&Number](std::initializer_list<double> Values)->TSharedPtr<FJsonValue>
    {
        TArray<TSharedPtr<FJsonValue>> Items; for (double Value:Values) Items.Add(Number(Value));
        return MakeShared<FJsonValueArray>(Items);
    };
    const auto Serialize=[](const TSharedPtr<FJsonObject>& Object)
    { FString Result; FJsonSerializer::Serialize(Object.ToSharedRef(),TJsonWriterFactory<>::Create(&Result)); return Result; };
    const auto DeepCopy=[&Serialize](const TSharedPtr<FJsonObject>& Object)
    {
        TSharedPtr<FJsonObject> Copy;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Serialize(Object)),Copy); return Copy;
    };
    const FString NativePolicyBefore=UWarImportLibrary::DescribeStaticMeshNativePolicy(Source);
    TSharedPtr<FJsonObject> SourcePolicyReport;
    if (!TestTrue(TEXT("Actual persistent native policy is readable without Python protected properties"),
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(NativePolicyBefore),SourcePolicyReport))) return false;
    TestTrue(TEXT("Native policy declares complete available read-only data"),SourcePolicyReport->GetBoolField(TEXT("readOnly"))
        && SourcePolicyReport->GetBoolField(TEXT("available")) && SourcePolicyReport->GetBoolField(TEXT("valid")));
    const auto SourcePolicy=SourcePolicyReport->GetObjectField(TEXT("policy"));
    TestEqual(TEXT("Policy exports all three actual source LODs"),int32(SourcePolicy->GetNumberField(TEXT("sourceLods"))),3);
    TestEqual(TEXT("Full reflected build policies cover all source LODs"),SourcePolicy->GetArrayField(TEXT("buildSettings")).Num(),3);
    TestEqual(TEXT("Full reflected reduction policies cover all source LODs"),SourcePolicy->GetArrayField(TEXT("reductionSettings")).Num(),3);
    TestEqual(TEXT("Protected automatic screen policy is read through its actual native accessor"),
        SourcePolicy->GetObjectField(TEXT("mesh"))->GetBoolField(TEXT("auto_compute_lod_screen_size")),Source->GetAutoComputeLODScreenSize());
    TestTrue(TEXT("Native policy retains complete reflected Nanite settings"),SourcePolicy->GetObjectField(TEXT("mesh"))->GetObjectField(TEXT("nanite_settings"))->Values.Num()>10);
    TestEqual(TEXT("Selected collision complexity comes from actual persistent BodySetup"),
        int32(SourcePolicy->GetObjectField(TEXT("bodySetup"))->GetNumberField(TEXT("collision_trace_flag"))),int32(OriginalBody->CollisionTraceFlag));
    const int32 OldLightmapSource=Source->GetSourceModel(0).BuildSettings.SrcLightmapIndex;
    Source->GetSourceModel(0).BuildSettings.SrcLightmapIndex=17;
    const FString ChangedPolicy=UWarImportLibrary::DescribeStaticMeshNativePolicy(Source);
    TestNotEqual(TEXT("Readback observes real reflected source policy changes without a mesh rebuild"),ChangedPolicy,NativePolicyBefore);
    Source->GetSourceModel(0).BuildSettings.SrcLightmapIndex=OldLightmapSource;
    TestEqual(TEXT("Restoring the fixture policy yields the exact original native receipt"),UWarImportLibrary::DescribeStaticMeshNativePolicy(Source),NativePolicyBefore);
    const auto OriginalData=Export->GetObjectField(TEXT("data"));
    auto Data=DeepCopy(OriginalData);
    auto Positions=Data->GetArrayField(TEXT("positions"));
    Positions.Add(Vector({960,60,6000})); Positions.Add(Vector({960,0,6000}));
    Data->SetArrayField(TEXT("positions"),Positions);
    const double Weights[2][3]={{0,.5,.5},{.5,0,.5}};
    for (const TCHAR* Key : {TEXT("normals"),TEXT("uvs"),TEXT("vertexColors"),TEXT("tangents")})
    {
        auto Values=Data->GetArrayField(Key); const int32 Dimension=Values[6]->AsArray().Num();
        for (const auto& Weight:Weights)
        {
            TArray<TSharedPtr<FJsonValue>> Value;
            for (int32 Axis=0;Axis<Dimension;++Axis)
            {
                double Total=0;for (int32 Corner=0;Corner<3;++Corner) Total+=Weight[Corner]*Values[6+Corner]->AsArray()[Axis]->AsNumber();
                Value.Add(Number(Total));
            }
            Values.Add(MakeShared<FJsonValueArray>(Value));
        }
        Data->SetArrayField(Key,Values);
    }
    auto Channels=Data->GetArrayField(TEXT("uvChannels"));
    for (auto& Channel:Channels)
    {
        auto Values=Channel->AsArray();
        for (const auto& Weight:Weights)
        {
            TArray<TSharedPtr<FJsonValue>> Value;
            for (int32 Axis=0;Axis<2;++Axis)
            {
                double Total=0;for (int32 Corner=0;Corner<3;++Corner) Total+=Weight[Corner]*Values[6+Corner]->AsArray()[Axis]->AsNumber();
                Value.Add(Number(Total));
            }
            Values.Add(MakeShared<FJsonValueArray>(Value));
        }
        Channel=MakeShared<FJsonValueArray>(Values);
    }
    Data->SetArrayField(TEXT("uvChannels"),Channels);
    auto Signs=Data->GetArrayField(TEXT("binormalSigns"));Signs.Add(Number(0));Signs.Add(Number(0));
    Data->SetArrayField(TEXT("binormalSigns"),Signs);
    TArray<TSharedPtr<FJsonValue>> OutputIndices;
    for (int32 Index:{0,1,2,3,4,5,6,7,9,6,9,10}) OutputIndices.Add(Number(Index));
    Data->SetArrayField(TEXT("indices"),OutputIndices);
    Data->SetArrayField(TEXT("triangleMaterials"),{Number(1),Number(0),Number(1),Number(1)});

    TSharedPtr<FJsonValue> Frame,Volumes,Local;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(TEXT("{\"translationCm\":[25000,0,0],\"rotationQuaternion\":[0,0,0,1],\"scale\":[1,1,1]}")),Frame);
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(TEXT("[{\"id\":\"occupied_commander_hall\",\"coordinateSpace\":\"world_cm\",\"bounds\":[[25960,-4260,5980],[33460,4260,24000]]}]")),Volumes);
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(TEXT("[[[960,-4260,5980],[8460,4260,24000]]]")),Local);
    auto Receipt=MakeShared<FJsonObject>();
    Receipt->SetNumberField(TEXT("schemaVersion"),1);Receipt->SetBoolField(TEXT("geometryOnly"),true);
    Receipt->SetStringField(TEXT("method"),TEXT("convex_halfspace_difference_source_corner_barycentrics"));
    Receipt->SetStringField(TEXT("winding"),TEXT("preserve_input_index_order"));
    Receipt->SetField(TEXT("actorTransform"),Frame);Receipt->SetField(TEXT("worldVolumes"),Volumes);Receipt->SetField(TEXT("localVolumeBounds"),Local);
    Receipt->SetNumberField(TEXT("sourceTriangles"),3);Receipt->SetNumberField(TEXT("outputTriangles"),4);
    Receipt->SetArrayField(TEXT("touchedSourceTriangles"),{Number(2)});Receipt->SetArrayField(TEXT("fullyRemovedSourceTriangles"),{});
    TArray<TSharedPtr<FJsonValue>> Boundary;
    for (int32 Index=0;Index<2;++Index)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("index"),9+Index);
        Row->SetArrayField(TEXT("sourceIndices"),{Number(6),Number(7),Number(8)});
        Row->SetArrayField(TEXT("weights"),{Number(Weights[Index][0]),Number(Weights[Index][1]),Number(Weights[Index][2])});
        Boundary.Add(MakeShared<FJsonValueObject>(Row));
    }
    Receipt->SetArrayField(TEXT("addedBoundaryVertices"),Boundary);
    auto Outside=MakeShared<FJsonObject>();Outside->SetArrayField(TEXT("sourceTriangleIds"),{Number(0),Number(1)});
    Receipt->SetObjectField(TEXT("outsidePreservation"),Outside);
    auto Wrapper=MakeShared<FJsonObject>();Wrapper->SetNumberField(TEXT("schemaVersion"),1);
    Wrapper->SetStringField(TEXT("sourceMesh"),Source->GetPathName());Wrapper->SetStringField(TEXT("sourceExportPayload"),Raw);
    Wrapper->SetStringField(TEXT("sourceExportSha256"),RawHash);
    Wrapper->SetField(TEXT("actorTransform"),Frame);Wrapper->SetField(TEXT("worldVolumes"),Volumes);Wrapper->SetField(TEXT("localVolumeBounds"),Local);
    Wrapper->SetObjectField(TEXT("data"),Data);Wrapper->SetObjectField(TEXT("carveReceipt"),Receipt);
    const FString GoodJson=Serialize(Wrapper);
    const auto Collection=[]() { return TEXT("AegisCitadel_")+FGuid::NewGuid().ToString(EGuidFormats::Digits).ToLower().Left(12); };
    const FString TargetCollection=Collection();
    TArray<FMeshBuildSettings> Settings;TArray<FMeshReductionSettings> Reductions;
    for (int32 Lod=0;Lod<Source->GetNumSourceModels();++Lod)
    {Settings.Add(Source->GetSourceModel(Lod).BuildSettings);Reductions.Add(Source->GetSourceModel(Lod).ReductionSettings);}
    const auto* SourceRender=Source->GetRenderData();
    const FGuid SourceBodyGuid=OriginalBody->BodySetupGuid;
    const FVertexID PendingVertex=*Working->Vertices().GetElementIDs().begin();
    const FVector3f PendingPosition(10001,10002,10003);
    FStaticMeshAttributes(*Working).GetVertexPositions()[PendingVertex]=PendingPosition;
    auto* Clone=UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(Source,TargetCollection,GoodJson);
    if (!TestNotNull(TEXT("Verified crossing face produces an actual unsaved native clone"),Clone)) return false;
    TSharedPtr<FJsonObject> ClonePolicyReport;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshNativePolicy(Clone)),ClonePolicyReport)) return false;
    TestTrue(TEXT("Actual native clone policy is readable and valid"),ClonePolicyReport->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("Full source/reduction/Nanite/mesh/BodySetup policies survive actual cloning"),
        Serialize(ClonePolicyReport->GetObjectField(TEXT("policy"))),Serialize(SourcePolicy));
    TestEqual(TEXT("Private helper creates only the fixed owned mesh"),Clone->GetPathName(),
        TEXT("/Game/WorldRebuild/")+TargetCollection+TEXT("/Meshes/SM_HallCarvedMountain.SM_HallCarvedMountain"));
    TestFalse(TEXT("Clone is never saved by this helper"),FPackageName::DoesPackageExist(Clone->GetOutermost()->GetName()));
    TestEqual(TEXT("All original source models are retained"),Clone->GetNumSourceModels(),Source->GetNumSourceModels());
    for (int32 Lod=0;Lod<Source->GetNumSourceModels();++Lod)
    {
        TestTrue(TEXT("Every native source LOD build policy is inherited unchanged"),Clone->GetSourceModel(Lod).BuildSettings==Settings[Lod]);
        TestTrue(TEXT("Every native source LOD reduction policy is inherited unchanged"),Clone->GetSourceModel(Lod).ReductionSettings==Reductions[Lod]);
    }
    TestEqual(TEXT("Every inherited source LOD has actual built render data"),Clone->GetRenderData()->LODResources.Num(),3);
    TestEqual(TEXT("Original collision LOD remains active"),Clone->LODForCollision,Source->LODForCollision);
    TestEqual(TEXT("Original collision trace policy remains active"),int32(Clone->GetBodySetup()->CollisionTraceFlag),int32(OriginalBody->CollisionTraceFlag));
    TestEqual(TEXT("Original double-sided policy is copied"),bool(Clone->GetBodySetup()->bDoubleSidedGeometry),true);
    TestTrue(TEXT("Rebuilt clone has its own BodySetup"),Clone->GetBodySetup()!=OriginalBody);
    FTriMeshCollisionData Collision;
    if (!TestTrue(TEXT("Clone exposes actual rebuilt collision triangles"),Clone->GetPhysicsTriMeshData(&Collision,true))) return false;
    TestEqual(TEXT("Collision consumes all four actual clipped LOD0 faces"),Collision.Indices.Num(),4);
    for (int32 Slot=0;Slot<Source->GetStaticMaterials().Num();++Slot)
    {
        TestEqual(TEXT("Material slot identity is preserved"),Clone->GetStaticMaterials()[Slot].MaterialSlotName,Source->GetStaticMaterials()[Slot].MaterialSlotName);
        TestTrue(TEXT("Actual material object is retained"),Clone->GetStaticMaterials()[Slot].MaterialInterface==Source->GetStaticMaterials()[Slot].MaterialInterface);
    }
    FMeshDescription Stored;
    if (!TestTrue(TEXT("Clone contains actual committed corner data"),Clone->GetSourceModel(0).LoadMeshDescription(Stored))) return false;
    const FStaticMeshConstAttributes StoredAttributes(Stored);
    FMeshDescription OriginalDescription;Source->GetSourceModel(0).LoadMeshDescription(OriginalDescription);
    const FStaticMeshConstAttributes OriginalAttributes(OriginalDescription);
    TestEqual(TEXT("Shared native vertices and all orphan vertices survive without corner explosion"),Stored.Vertices().Num(),OriginalDescription.Vertices().Num()+2);
    for (const FVertexID Vertex:OriginalDescription.Vertices().GetElementIDs())
        TestEqual(TEXT("Every original vertex ID and position, including orphans, is exact"),StoredAttributes.GetVertexPositions()[Vertex],OriginalAttributes.GetVertexPositions()[Vertex]);
    for (const FVertexInstanceID Instance:OriginalDescription.VertexInstances().GetElementIDs())
        TestEqual(TEXT("Original shared corner-to-vertex connectivity is exact"),Stored.GetVertexInstanceVertex(Instance),OriginalDescription.GetVertexInstanceVertex(Instance));
    for (const FEdgeID Edge:OriginalDescription.Edges().GetElementIDs())
    {
        const auto A=Stored.GetEdgeVertices(Edge),B=OriginalDescription.GetEdgeVertices(Edge);
        TestTrue(TEXT("All original edge IDs, endpoints and hardness survive"),A[0]==B[0] && A[1]==B[1] && StoredAttributes.GetEdgeHardnesses()[Edge]==OriginalAttributes.GetEdgeHardnesses()[Edge]);
    }
    TestEqual(TEXT("Unused original corner remains committed with all new boundary corners"),Stored.VertexInstances().Num(),11);
    TestEqual(TEXT("The clipped quad replaces only the touched source face"),Stored.Triangles().Num(),4);
    TestEqual(TEXT("All committed UV channels remain present"),StoredAttributes.GetVertexInstanceUVs().GetNumChannels(),2);
    const FVertexID CutVertex=Stored.GetVertexInstanceVertex(FVertexInstanceID(10));
    const FEdgeID SplitHardEdge=Stored.GetVertexPairEdge(FVertexID(6),CutVertex);
    TestTrue(TEXT("An actual split of a hard source edge retains hardness"),Stored.IsEdgeValid(SplitHardEdge) && StoredAttributes.GetEdgeHardnesses()[SplitHardEdge]);
    for (int32 Index=0;Index<11;++Index)
    {
        const FVertexInstanceID Corner(Index);
        const auto Position=StoredAttributes.GetVertexPositions()[Stored.GetVertexInstanceVertex(Corner)];
        const auto& P=Data->GetArrayField(TEXT("positions"))[Index]->AsArray();
        TestEqual(TEXT("Each committed original/boundary position is exact"),Position,FVector3f(float(P[0]->AsNumber()),float(P[1]->AsNumber()),float(P[2]->AsNumber())));
        for (const TCHAR* Key:{TEXT("normals"),TEXT("tangents")})
        {
            const auto& V=Data->GetArrayField(Key)[Index]->AsArray();
            const FVector3f Expected(float(V[0]->AsNumber()),float(V[1]->AsNumber()),float(V[2]->AsNumber()));
            TestEqual(TEXT("Committed source normals/tangents retain stored values including zeros"),
                FString(Key)==TEXT("normals")?StoredAttributes.GetVertexInstanceNormals()[Corner]:StoredAttributes.GetVertexInstanceTangents()[Corner],Expected);
        }
        const auto& C=Data->GetArrayField(TEXT("vertexColors"))[Index]->AsArray();
        TestEqual(TEXT("Original and boundary RGBA preserve all channels"),StoredAttributes.GetVertexInstanceColors()[Corner],
            FVector4f(float(C[0]->AsNumber()),float(C[1]->AsNumber()),float(C[2]->AsNumber()),float(C[3]->AsNumber())));
        TestEqual(TEXT("Authored negative and registered zero handedness remain exact"),StoredAttributes.GetVertexInstanceBinormalSigns()[Corner],float(Signs[Index]->AsNumber()));
        for (int32 Channel=0;Channel<2;++Channel)
        {
            const auto& UV=Channels[Channel]->AsArray()[Index]->AsArray();
            TestEqual(TEXT("UV channel seam and boundary interpolation remain exact"),StoredAttributes.GetVertexInstanceUVs().Get(Corner,Channel),
                FVector2f(float(UV[0]->AsNumber()),float(UV[1]->AsNumber())));
        }
    }
    int32 Offset=0,TriangleOrdinal=0;
    constexpr int32 SourceOrdinals[]={0,1,2,2};
    for (const FTriangleID Triangle:Stored.Triangles().GetElementIDs())
    {
        const auto Corners=Stored.GetTriangleVertexInstances(Triangle);
        for (int32 Corner=0;Corner<3;++Corner)
            TestEqual(TEXT("Clipping preserves actual original winding and unaffected corner indices"),Corners[Corner].GetValue(),int32(OutputIndices[Offset++]->AsNumber()));
        TestEqual(TEXT("Every original and split triangle retains its exact source polygon group"),
            Stored.GetTrianglePolygonGroup(Triangle).GetValue(),int32(Export->GetArrayField(TEXT("trianglePolygonGroupIds"))[SourceOrdinals[TriangleOrdinal++]]->AsNumber()));
    }
    const auto OriginalGroups=Export->GetArrayField(TEXT("polygonGroups"));
    TestEqual(TEXT("Source polygon group identities remain present"),Stored.PolygonGroups().Num(),OriginalGroups.Num());
    for (const auto& Value:OriginalGroups)
    {
        const auto Group=Value->AsObject();const FPolygonGroupID Id(int32(Group->GetNumberField(TEXT("id"))));
        TestEqual(TEXT("Source polygon group slot names are exact"),StoredAttributes.GetPolygonGroupMaterialSlotNames()[Id],FName(*Group->GetStringField(TEXT("slotName"))));
    }
    TestEqual(TEXT("Actual source committed JSON is immutable"),UWarImportLibrary::DescribeStaticMeshSourceData(Source),Raw);
    TestEqual(TEXT("All original stored topology is immutable"),UWarImportLibrary::DescribeStaticMeshStoredCorners(Source),OriginalTopology);
    TestEqual(TEXT("Original actual computed render faces are immutable"),UWarImportLibrary::DescribeStaticMeshRenderedFaces(Source),OriginalRendered);
    TSharedPtr<FJsonObject> OriginalFaces,CloneFaces;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(OriginalRendered),OriginalFaces)
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderedFaces(Clone)),CloneFaces)) return false;
    TestTrue(TEXT("Actual render face export is finite and complete"),OriginalFaces->GetBoolField(TEXT("valid")) && CloneFaces->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("Render export contains every actual source index face"),OriginalFaces->GetArrayField(TEXT("triangles")).Num(),3);
    TestEqual(TEXT("Render export contains every actual cloned index face"),CloneFaces->GetArrayField(TEXT("triangles")).Num(),4);
    const auto& BeforeFaces=OriginalFaces->GetArrayField(TEXT("triangles"));const auto& AfterFaces=CloneFaces->GetArrayField(TEXT("triangles"));
    for (const auto& Before:BeforeFaces)
    {
        const auto A=Before->AsObject();if (A->GetArrayField(TEXT("positions"))[0]->AsArray()[0]->AsNumber()>=900) continue;
        const auto* Match=AfterFaces.FindByPredicate([&A](const auto& Value)
        {const auto B=Value->AsObject();return FJsonValue::CompareEqual(*A->TryGetField(TEXT("positions")),*B->TryGetField(TEXT("positions")))
            && A->GetNumberField(TEXT("materialIndex"))==B->GetNumberField(TEXT("materialIndex"));});
        if (!TestNotNull(TEXT("Each untouched oriented rendered face survives"),Match)) return false;
        for (const TCHAR* Key:{TEXT("normals"),TEXT("tangents"),TEXT("binormals")})
            TestTrue(FString::Printf(TEXT("Untouched actual rendered %s match the original exactly"),Key),
                FJsonValue::CompareEqual(*A->TryGetField(Key),*(*Match)->AsObject()->TryGetField(Key)));
        const auto& OldChannels=A->GetArrayField(TEXT("uvChannels"));
        const auto& NewChannels=(*Match)->AsObject()->GetArrayField(TEXT("uvChannels"));
        TestEqual(TEXT("Actual rendered UV channel count is preserved"),NewChannels.Num(),OldChannels.Num());
        for (int32 Channel=0;Channel<OldChannels.Num();++Channel)
        {
            // Only the original declared lightmap destination may repack after clipping.
            // Committed UVs remain exact above; every authored rendered UV stays exact here.
            const bool Generated=Settings[0].bGenerateLightmapUVs && Channel==Settings[0].DstLightmapIndex;
            if (!Generated)
                TestTrue(FString::Printf(TEXT("Untouched authored rendered UV%d matches exactly"),Channel),
                    FJsonValue::CompareEqual(*OldChannels[Channel],*NewChannels[Channel]));
            else for (const auto& Value:{OldChannels[Channel],NewChannels[Channel]})
                for (const auto& UV:Value->AsArray()) for (const auto& Coordinate:UV->AsArray())
                {
                    const double AtlasCoordinate=Coordinate->AsNumber();
                    TestTrue(TEXT("Actual original-policy-generated lightmap coordinates remain finite within atlas bounds"),
                        FMath::IsFinite(AtlasCoordinate) && AtlasCoordinate>=-.001 && AtlasCoordinate<=1.001);
                }
        }
    }
    auto& RenderBuffer=Clone->GetRenderData()->LODResources[0].VertexBuffers.StaticMeshVertexBuffer;
    const auto BadFace=AfterFaces[0]->AsObject();const uint32 BadVertex=uint32(BadFace->GetArrayField(TEXT("vertexIds"))[0]->AsNumber());
    const FVector3f OldX(RenderBuffer.VertexTangentX(BadVertex)),OldY(RenderBuffer.VertexTangentY(BadVertex)),OldZ(RenderBuffer.VertexTangentZ(BadVertex));
    RenderBuffer.SetVertexTangents(BadVertex,FVector3f(0,1,0),FVector3f(1,0,0),FVector3f(0,0,1));
    TestNotEqual(TEXT("Actual render export observes finite basis corruption rather than source values"),UWarImportLibrary::DescribeStaticMeshRenderedFaces(Clone),Serialize(CloneFaces));
    RenderBuffer.SetVertexTangents(BadVertex,OldX,OldY,OldZ);
    TestEqual(TEXT("Read-only clone policy access preserves all actual original persistent policies"),UWarImportLibrary::DescribeStaticMeshNativePolicy(Source),NativePolicyBefore);
    TSharedPtr<FJsonObject> MissingPolicy;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshNativePolicy(nullptr)),MissingPolicy)) return false;
    TestFalse(TEXT("Missing native policy is explicitly unavailable rather than default-filled"),MissingPolicy->GetBoolField(TEXT("available")));
    TestFalse(TEXT("Missing native policy never declares valid source settings"),MissingPolicy->GetBoolField(TEXT("valid")));
    TestTrue(TEXT("Source render data was not rebuilt"),Source->GetRenderData()==SourceRender);
    TestEqual(TEXT("Original native collision data was not invalidated"),OriginalBody->BodySetupGuid,SourceBodyGuid);
    TestFalse(TEXT("Original package dirty state is retained"),Source->GetOutermost()->IsDirty());
    TestEqual(TEXT("Clone construction does not overwrite pending original editor positions"),FStaticMeshAttributes(*Working).GetVertexPositions()[PendingVertex],PendingPosition);
    TestTrue(TEXT("Original pending source cache retains registered zero tangents"),Attributes.GetVertexInstanceTangents()[FVertexInstanceID(6)].IsZero());
    TestNull(TEXT("An existing private target cannot be overwritten"),UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(Source,TargetCollection,GoodJson));
    TestNull(TEXT("Public importer refuses every technical source fixture"),UWarImportLibrary::CreateCarvedCitadelTerrain(Source,Collection(),GoodJson));
    TestNull(TEXT("Uppercase namespace is outside authorized target scope"),UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(Source,TEXT("AegisCitadel_ABCDEF123456"),GoodJson));
    TestNull(TEXT("Parent traversal cannot select another target path"),UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(Source,TEXT("AegisCitadel_../../foreign"),GoodJson));

    const auto Reject=[this,Source,&DeepCopy,&Serialize,&Collection,&Wrapper](const TCHAR* Label,auto Mutate)
    {
        auto Bad=DeepCopy(Wrapper);Mutate(Bad);
        const FString Namespace=Collection();
        TestNull(Label,UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(Source,Namespace,Serialize(Bad)));
        TestNull(TEXT("Rejected document allocates no private Content package"),FindPackage(nullptr,*(TEXT("/Game/WorldRebuild/")+Namespace+TEXT("/Meshes/SM_HallCarvedMountain"))));
    };
    Reject(TEXT("Changed raw source hash rejects before allocation"),[](auto Bad){Bad->SetStringField(TEXT("sourceExportSha256"),FString::ChrN(64,TEXT('0')));});
    Reject(TEXT("Unknown wrapper members reject before allocation"),[](auto Bad){Bad->SetBoolField(TEXT("approval"),true);});
    Reject(TEXT("Unknown schema version cannot reinterpret source geometry"),[](auto Bad){Bad->SetNumberField(TEXT("schemaVersion"),2);});
    Reject(TEXT("Dropped registered tangent data is never flattened"),[](auto Bad){Bad->GetObjectField(TEXT("data"))->RemoveField(TEXT("tangents"));});
    Reject(TEXT("Original corner positions cannot be edited by the carve"),[&Vector](auto Bad)
    {auto D=Bad->GetObjectField(TEXT("data"));auto Values=D->GetArrayField(TEXT("positions"));Values[0]=Vector({1,0,0});D->SetArrayField(TEXT("positions"),Values);});
    Reject(TEXT("Original additional UV channels cannot be edited"),[&Vector](auto Bad)
    {auto D=Bad->GetObjectField(TEXT("data"));auto Values=D->GetArrayField(TEXT("uvChannels"));auto Channel=Values[1]->AsArray();Channel[0]=Vector({.99,.99});Values[1]=MakeShared<FJsonValueArray>(Channel);D->SetArrayField(TEXT("uvChannels"),Values);});
    Reject(TEXT("An exterior face cannot be reversed"),[](auto Bad)
    {auto D=Bad->GetObjectField(TEXT("data"));auto Values=D->GetArrayField(TEXT("indices"));Swap(Values[1],Values[2]);D->SetArrayField(TEXT("indices"),Values);});
    Reject(TEXT("Original face material assignment cannot be changed"),[&Number](auto Bad)
    {auto D=Bad->GetObjectField(TEXT("data"));auto Values=D->GetArrayField(TEXT("triangleMaterials"));Values[0]=Number(0);D->SetArrayField(TEXT("triangleMaterials"),Values);});
    Reject(TEXT("Boundary weights must derive the actual source corner"),[&Number](auto Bad)
    {Bad->GetObjectField(TEXT("carveReceipt"))->GetArrayField(TEXT("addedBoundaryVertices"))[0]->AsObject()->SetArrayField(TEXT("weights"),{Number(0),Number(.25),Number(.75)});});
    Reject(TEXT("A crossing source face cannot be declared wholly removed"),[&Number](auto Bad)
    {Bad->GetObjectField(TEXT("carveReceipt"))->SetArrayField(TEXT("fullyRemovedSourceTriangles"),{Number(2)});});
    Reject(TEXT("A partial exterior crossing fragment cannot be dropped"),[](auto Bad)
    {
        auto D=Bad->GetObjectField(TEXT("data"));auto Indices=D->GetArrayField(TEXT("indices"));Indices.SetNum(9);
        auto Materials=D->GetArrayField(TEXT("triangleMaterials"));Materials.SetNum(3);
        D->SetArrayField(TEXT("indices"),Indices);D->SetArrayField(TEXT("triangleMaterials"),Materials);
        Bad->GetObjectField(TEXT("carveReceipt"))->SetNumberField(TEXT("outputTriangles"),3);
    });
    Reject(TEXT("A surviving exterior fragment cannot replace another with a duplicate"),[](auto Bad)
    {
        auto D=Bad->GetObjectField(TEXT("data"));auto Indices=D->GetArrayField(TEXT("indices"));
        for (int32 Corner=0;Corner<3;++Corner) Indices[9+Corner]=Indices[6+Corner];
        D->SetArrayField(TEXT("indices"),Indices);
    });
    TestEqual(TEXT("All rejected calls leave original committed data intact"),UWarImportLibrary::DescribeStaticMeshSourceData(Source),Raw);
    TestFalse(TEXT("All rejected calls retain original package dirty state"),Source->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelSourceDataTest, "AegisWar.Foundation.CitadelSourceData",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCitadelSourceDataTest::RunTest(const FString& Parameters)
{
    const auto Read = [this](UStaticMesh* Surface, int32 Lod = 0)
    {
        TSharedPtr<FJsonObject> Result;
        TestTrue(TEXT("Source inspection returns readable JSON"), FJsonSerializer::Deserialize(
            TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshSourceData(Surface, Lod)), Result));
        return Result;
    };
    const auto Missing = Read(nullptr);
    if (!Missing) return false;
    TestFalse(TEXT("Missing mesh has no invented source geometry"), Missing->GetBoolField(TEXT("available")));
    auto* Material = UMaterial::GetDefaultMaterial(MD_Surface);
    auto* Mesh = UWarImportLibrary::CreateCompositeWorldSurface(TEXT("CitadelSourceAutomation"),
        TEXT("Corners_") + FGuid::NewGuid().ToString(EGuidFormats::Digits),
        {{0,0,0},{100,0,0},{0,100,0},{0,0,0},{0,100,0},{0,0,100}}, {0,2,1,3,5,4},
        {{0,0,1},{0,0,1},{0,0,1},{1,0,0},{1,0,0},{1,0,0}},
        {{0,0},{1,0},{0,1},{.25,.25},{.5,.75},{1,.5}},
        {FLinearColor(.1f,.2f,.3f,.4f),FLinearColor(.2f,.3f,.4f,.5f),FLinearColor(.3f,.4f,.5f,.6f),
         FLinearColor(.4f,.5f,.6f,.7f),FLinearColor(.5f,.6f,.7f,.8f),FLinearColor(.6f,.7f,.8f,.9f)},
        {1,0}, {Material,Material}, false);
    if (!TestNotNull(TEXT("Actual multi-material corner fixture is built"), Mesh)) return false;
    FMeshDescription* Working = Mesh->GetMeshDescription(0);
    if (!TestNotNull(TEXT("Actual editable source description exists"), Working)) return false;
    FStaticMeshAttributes Attributes(*Working);
    auto UVs = Attributes.GetVertexInstanceUVs(); UVs.SetNumChannels(2);
    const auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    for (const FVertexInstanceID Corner : Working->VertexInstances().GetElementIDs())
    {
        UVs.Set(Corner,1,FVector2f(Corner.GetValue()*.125f,1.f-Corner.GetValue()*.125f));
        Signs[Corner] = Corner.GetValue()%2 ? -1.f : 1.f;
    }
    const FVertexID UnusedVertex=Working->CreateVertex();
    const FVertexInstanceID UnusedCorner=Working->CreateVertexInstance(UnusedVertex);
    Attributes.GetVertexPositions()[UnusedVertex]=FVector3f(321,654,987);
    Attributes.GetVertexInstanceNormals()[UnusedCorner]=FVector3f(0,1,0);
    Attributes.GetVertexInstanceTangents()[UnusedCorner]=FVector3f::ZeroVector;
    Attributes.GetVertexInstanceBinormalSigns()[UnusedCorner]=0;
    Attributes.GetVertexInstanceColors()[UnusedCorner]=FVector4f(.25,.5,.75,1);
    UVs.Set(UnusedCorner,0,FVector2f(.125,.875));UVs.Set(UnusedCorner,1,FVector2f(.375,.625));
    UStaticMesh::FCommitMeshDescriptionParams Commit;
    Commit.bMarkPackageDirty = false; Mesh->CommitMeshDescription(0,Commit);
    Mesh->GetOutermost()->SetDirtyFlag(false);
    const FMeshBuildSettings Settings = Mesh->GetSourceModel(0).BuildSettings;
    const auto* RenderData = Mesh->GetRenderData();
    const auto Good = Read(Mesh);
    if (!Good || !TestTrue(TEXT("Committed description is available"), Good->GetBoolField(TEXT("available")))) return false;
    TestTrue(TEXT("Finite source corners and original material slots are valid"), Good->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("Source read policy excludes a pending working copy"), Good->GetStringField(TEXT("sourcePolicy")),
        FString(TEXT("committed_mesh_description_bulk_data_no_working_copy")));
    TestEqual(TEXT("All material slots are retained in order"), Good->GetArrayField(TEXT("materialSlots")).Num(),2);
    const auto Data = Good->GetObjectField(TEXT("data"));
    TestEqual(TEXT("Two triangles expand to six actual source corners"), Data->GetArrayField(TEXT("positions")).Num(),6);
    TestEqual(TEXT("Original triangle material order is preserved"), Data->GetArrayField(TEXT("triangleMaterials"))[0]->AsNumber(),1.);
    TestEqual(TEXT("Second triangle retains material0"), Data->GetArrayField(TEXT("triangleMaterials"))[1]->AsNumber(),0.);
    TestEqual(TEXT("Native winding retains the clockwise second corner Y"),
        Data->GetArrayField(TEXT("positions"))[1]->AsArray()[1]->AsNumber(),100.);
    TestEqual(TEXT("Coincident hard-edge corners retain their distinct normals"),
        Data->GetArrayField(TEXT("normals"))[3]->AsArray()[0]->AsNumber(),1.);
    TestEqual(TEXT("All committed UV channels are retained"),Data->GetArrayField(TEXT("uvChannels")).Num(),2);
    TestEqual(TEXT("Committed UV1 remains unchanged"),Data->GetArrayField(TEXT("uvChannels"))[1]
        ->AsArray()[1]->AsArray()[0]->AsNumber(),.125);
    TestEqual(TEXT("Committed vertex color uses original named RGBA"),Data->GetArrayField(TEXT("vertexColors"))[0]
        ->AsArray()[0]->AsNumber(),double(.1f));
    TestEqual(TEXT("Negative authored binormal sign remains negative"),Data->GetArrayField(TEXT("binormalSigns"))[1]->AsNumber(),-1.);
    TestEqual(TEXT("Actual stored tangents are retained"),Data->GetArrayField(TEXT("tangents"))[0]->AsArray()[1]->AsNumber(),1.);
    for (int32 Corner=0;Corner<6;++Corner)
        TestEqual(TEXT("Expanded indices preserve exact corner order"),Data->GetArrayField(TEXT("indices"))[Corner]->AsNumber(),double(Corner));

    const FString ReferencedBefore=UWarImportLibrary::DescribeStaticMeshSourceData(Mesh);
    TSharedPtr<FJsonObject> Stored;
    if (!TestTrue(TEXT("Complete committed stored-corner inspection returns readable JSON"),FJsonSerializer::Deserialize(
        TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshStoredCorners(Mesh)),Stored))) return false;
    TestTrue(TEXT("Stored-corner inspection is read-only and valid"),Stored->GetBoolField(TEXT("readOnly")) && Stored->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("All seven actual stored instances include the unused corner"),Stored->GetNumberField(TEXT("sourceVertexInstanceCount")),7.);
    TestEqual(TEXT("Actual instance-ID order includes the unused native ID"),Stored->GetArrayField(TEXT("instanceIds"))[6]->AsNumber(),double(UnusedCorner.GetValue()));
    TestEqual(TEXT("Actual corner-to-vertex mapping is retained"),Stored->GetArrayField(TEXT("vertexIds"))[6]->AsNumber(),double(UnusedVertex.GetValue()));
    const auto StoredData=Stored->GetObjectField(TEXT("data"));
    TestEqual(TEXT("Unused committed position survives full readback"),StoredData->GetArrayField(TEXT("positions"))[6]->AsArray()[0]->AsNumber(),321.);
    TestEqual(TEXT("Unused committed normal survives full readback"),StoredData->GetArrayField(TEXT("normals"))[6]->AsArray()[1]->AsNumber(),1.);
    TestEqual(TEXT("Registered unused zero tangent is not normalized or invented"),StoredData->GetArrayField(TEXT("tangents"))[6]->AsArray()[1]->AsNumber(),0.);
    TestEqual(TEXT("Registered unused zero handedness is not replaced"),StoredData->GetArrayField(TEXT("binormalSigns"))[6]->AsNumber(),0.);
    TestEqual(TEXT("Unused corner RGBA remains complete"),StoredData->GetArrayField(TEXT("vertexColors"))[6]->AsArray()[2]->AsNumber(),.75);
    TestEqual(TEXT("Unused second UV channel remains complete"),StoredData->GetArrayField(TEXT("uvChannels"))[1]->AsArray()[6]->AsArray()[0]->AsNumber(),.375);
    TestEqual(TEXT("Complete inspection leaves the existing expanded source output unchanged"),UWarImportLibrary::DescribeStaticMeshSourceData(Mesh),ReferencedBefore);
    const FString StoredBefore=UWarImportLibrary::DescribeStaticMeshStoredCorners(Mesh);

    // A readback must neither export a volatile edit as committed nor overwrite that editor edit.
    Working = Mesh->GetMeshDescription(0);
    FStaticMeshAttributes Pending(*Working);
    const FVertexID FirstVertex = *Working->Vertices().GetElementIDs().begin();
    const FVector3f PendingPosition(9001,9002,9003);
    Pending.GetVertexPositions()[FirstVertex] = PendingPosition;
    const FString CommittedJson = UWarImportLibrary::DescribeStaticMeshSourceData(Mesh);
    const FString Again = UWarImportLibrary::DescribeStaticMeshSourceData(Mesh);
    TestEqual(TEXT("Repeated committed source inspection is deterministic"),Again,CommittedJson);
    const auto Uncommitted = Read(Mesh);
    if (!Uncommitted) return false;
    TestEqual(TEXT("Pending source positions do not replace committed source"),Uncommitted->GetObjectField(TEXT("data"))
        ->GetArrayField(TEXT("positions"))[0]->AsArray()[0]->AsNumber(),0.);
    TestEqual(TEXT("Inspection preserves the actual pending editor position"),Pending.GetVertexPositions()[FirstVertex],PendingPosition);
    TestEqual(TEXT("Stored-corner readback excludes pending editor changes"),UWarImportLibrary::DescribeStaticMeshStoredCorners(Mesh),StoredBefore);
    TestFalse(TEXT("Source inspection leaves package dirty state unchanged"),Mesh->GetOutermost()->IsDirty());
    TestTrue(TEXT("Source inspection never rebuilds render data"),Mesh->GetRenderData()==RenderData);
    TestTrue(TEXT("Source inspection preserves build settings"),Mesh->GetSourceModel(0).BuildSettings==Settings);
    const auto Negative = Read(Mesh,-1), NoLod = Read(Mesh,1);
    if (!Negative || !NoLod) return false;
    TestFalse(TEXT("Negative source LOD is unavailable"),Negative->GetBoolField(TEXT("available")));
    TestFalse(TEXT("Missing source LOD is unavailable"),NoLod->GetBoolField(TEXT("available")));
    TSharedPtr<FJsonObject> MissingStored;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshStoredCorners(nullptr)),MissingStored)) return false;
    TestFalse(TEXT("Missing complete corner data is explicitly unavailable"),MissingStored->GetBoolField(TEXT("available")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelRenderBuffersTest, "AegisWar.Foundation.CitadelRenderBuffers",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCitadelRenderBuffersTest::RunTest(const FString& Parameters)
{
    TSharedPtr<FJsonObject> Missing;
    TestTrue(TEXT("Missing mesh returns readable diagnostic JSON"), FJsonSerializer::Deserialize(
        TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(nullptr)), Missing));
    if (!Missing) return false;
    TestFalse(TEXT("Missing render data cannot be approved"), Missing->GetBoolField(TEXT("available")));

    // Unsaved technical fixture: the native clockwise face retains its supplied outward normal.
    auto* Mesh = UWarImportLibrary::CreateWorldSurface(TEXT("CitadelImportAutomation"),
        FString(TEXT("Buffers_")) + FGuid::NewGuid().ToString(EGuidFormats::Digits),
        {{0,0,0}, {100,0,0}, {0,100,0}}, {0,2,1},
        {{0,0,1}, {0,0,1}, {0,0,1}}, {{0,0}, {1,0}, {0,1}},
        UMaterial::GetDefaultMaterial(MD_Surface), false);
    TestNotNull(TEXT("Real native mesh fixture was built"), Mesh);
    if (!Mesh) return false;
    TSharedPtr<FJsonObject> Good;
    TestTrue(TEXT("Built render buffers return diagnostic JSON"), FJsonSerializer::Deserialize(
        TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(Mesh)), Good));
    if (!Good || !Good->GetBoolField(TEXT("available"))) return false;
    const auto Row = Good->GetArrayField(TEXT("lods"))[0]->AsObject();
    TestTrue(TEXT("Actual buffer is readable"), Row->GetBoolField(TEXT("cpuReadable")));
    TestTrue(TEXT("Actual render UV channel exists"), Row->GetNumberField(TEXT("uvChannels")) >= 1.);
    TestEqual(TEXT("All built normals match committed source"), Row->GetNumberField(TEXT("committedSourceNormalMatches")), 3.);
    TestEqual(TEXT("Source vertices remain present"), Row->GetNumberField(TEXT("committedSourcePositionMissing")), 0.);
    TestEqual(TEXT("No built normal is reversed"), Row->GetNumberField(TEXT("committedSourceNormalDifferent")), 0.);
    TestEqual(TEXT("Built UVs are finite"), Row->GetNumberField(TEXT("invalidUVs")), 0.);
    TestEqual(TEXT("Built face retains its oriented source corners"),
        Row->GetNumberField(TEXT("committedSourceTriangleMatches")), 1.);
    TestEqual(TEXT("Built face remains present"), Row->GetNumberField(TEXT("committedSourceTrianglesMissing")), 0.);
    TestEqual(TEXT("Built corner attributes remain unchanged"), Row->GetNumberField(TEXT("committedSourceTrianglesDifferent")), 0.);
    const auto Basis = Row->GetObjectField(TEXT("tangentBasis"));
    TestTrue(TEXT("Tangent inspection is diagnostic rather than a mesh edit"), Basis->GetBoolField(TEXT("diagnosticOnly")));
    TestEqual(TEXT("Healthy native render basis has no invalid vertices"), Basis->GetNumberField(TEXT("invalidVertices")), 0.);
    TestEqual(TEXT("Every healthy native basis is orthogonal"), Basis->GetNumberField(TEXT("orthogonalVertices")), 3.);
    TestEqual(TEXT("Healthy bases produce no bad-vertex samples"), Basis->GetArrayField(TEXT("badVertexSamples")).Num(), 0);
    for (const TCHAR* Axis : {TEXT("x"), TEXT("y"), TEXT("z")})
    {
        const auto AxisRow = Basis->GetObjectField(TEXT("axes"))->GetObjectField(Axis);
        TestEqual(FString::Printf(TEXT("Native %s is finite"), Axis), AxisRow->GetNumberField(TEXT("finite")), 3.);
        TestEqual(FString::Printf(TEXT("Native %s is unit length"), Axis), AxisRow->GetNumberField(TEXT("unit")), 3.);
        TestEqual(FString::Printf(TEXT("Native %s is not nearly zero"), Axis), AxisRow->GetNumberField(TEXT("nearZero")), 0.);
    }

    auto& Buffer = Mesh->GetRenderData()->LODResources[0].VertexBuffers.StaticMeshVertexBuffer;
    const FVector3f OriginalX(Buffer.VertexTangentX(0)), OriginalY(Buffer.VertexTangentY(0)), OriginalZ(Buffer.VertexTangentZ(0));
    UWarImportLibrary::DescribeStaticMeshRenderData(Mesh);
    TestEqual(TEXT("Inspection leaves actual tangent X unchanged"), FVector3f(Buffer.VertexTangentX(0)), OriginalX);
    TestEqual(TEXT("Inspection leaves actual tangent Y unchanged"), FVector3f(Buffer.VertexTangentY(0)), OriginalY);
    TestEqual(TEXT("Inspection leaves actual tangent Z unchanged"), FVector3f(Buffer.VertexTangentZ(0)), OriginalZ);
    for (uint32 Vertex = 0; Vertex < Buffer.GetNumVertices(); ++Vertex)
        Buffer.SetVertexTangents(Vertex, FVector3f(1,0,0), FVector3f(0,-1,0), FVector3f(0,0,-1));
    TSharedPtr<FJsonObject> Reversed;
    TestTrue(TEXT("Corrupt actual buffer is still inspectable"), FJsonSerializer::Deserialize(
        TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(Mesh)), Reversed));
    if (!Reversed) return false;
    TestEqual(TEXT("Reversed render normals cannot pass source matching"), Reversed->GetArrayField(TEXT("lods"))[0]
        ->AsObject()->GetNumberField(TEXT("committedSourceNormalDifferent")), 3.);

    const auto Diagnose = [this, Mesh]() -> TSharedPtr<FJsonObject>
    {
        TSharedPtr<FJsonObject> Diagnostic;
        if (!TestTrue(TEXT("Modified temporary render basis remains inspectable"), FJsonSerializer::Deserialize(
            TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(Mesh)), Diagnostic))) return nullptr;
        return Diagnostic->GetArrayField(TEXT("lods"))[0]->AsObject()->GetObjectField(TEXT("tangentBasis"));
    };
    for (uint32 Vertex = 0; Vertex < Buffer.GetNumVertices(); ++Vertex)
        Buffer.SetVertexTangents(Vertex, FVector3f::ZeroVector, FVector3f(0,1,0), FVector3f(0,0,1));
    const auto ZeroBasis = Diagnose(); if (!ZeroBasis) return false;
    TestEqual(TEXT("A zero packed tangent is counted"), ZeroBasis->GetObjectField(TEXT("axes"))->GetObjectField(TEXT("x"))->GetNumberField(TEXT("nearZero")), 3.);
    TestEqual(TEXT("Its reconstructed zero binormal is counted"), ZeroBasis->GetObjectField(TEXT("axes"))->GetObjectField(TEXT("y"))->GetNumberField(TEXT("nearZero")), 3.);
    TestEqual(TEXT("Degenerate pairs are skipped rather than reported orthogonal"), ZeroBasis->GetObjectField(TEXT("pairs"))->GetObjectField(TEXT("xz"))->GetNumberField(TEXT("skipped")), 3.);
    TestEqual(TEXT("A zero tangent does not invalidate the actual unit normal"), ZeroBasis->GetObjectField(TEXT("axes"))->GetObjectField(TEXT("z"))->GetNumberField(TEXT("unit")), 3.);
    const auto ZeroSamples = ZeroBasis->GetArrayField(TEXT("badVertexSamples"));
    TestEqual(TEXT("Small failures retain every actual vertex sample"), ZeroSamples.Num(), 3);
    if (ZeroSamples.Num() != 3) return false;
    for (int32 Index = 0; Index < ZeroSamples.Num(); ++Index)
    {
        const auto Sample = ZeroSamples[Index]->AsObject();
        const auto Position = Mesh->GetRenderData()->LODResources[0].VertexBuffers.PositionVertexBuffer.VertexPosition(Index);
        const auto UV = Buffer.GetVertexUV(Index, 0);
        TestEqual(TEXT("Bad sample retains the actual native vertex index"), Sample->GetNumberField(TEXT("index")), double(Index));
        TestEqual(TEXT("Bad sample retains actual position X"), Sample->GetArrayField(TEXT("position"))[0]->AsNumber(), double(Position.X));
        TestEqual(TEXT("Bad sample retains actual UV0 X"), Sample->GetArrayField(TEXT("uv0"))[0]->AsNumber(), double(UV.X));
        TestEqual(TEXT("Bad sample retains actual normal Z"), Sample->GetArrayField(TEXT("z"))[2]->AsNumber(), double(FVector3f(Buffer.VertexTangentZ(Index)).Z));
        TestTrue(TEXT("Zero tangent sample identifies its failed axis"), Sample->GetObjectField(TEXT("axisFlags"))->GetObjectField(TEXT("x"))->GetBoolField(TEXT("nearZero")));
        TestTrue(TEXT("Degenerate sample distinguishes skipped orthogonality"), Sample->GetObjectField(TEXT("pairFlags"))->GetObjectField(TEXT("xz"))->GetBoolField(TEXT("skipped")));
    }
    for (uint32 Vertex = 0; Vertex < Buffer.GetNumVertices(); ++Vertex)
        Buffer.SetVertexTangents(Vertex, FVector3f(0,0,1), FVector3f(0,1,0), FVector3f(0,0,1));
    const auto ParallelBasis = Diagnose(); if (!ParallelBasis) return false;
    TestEqual(TEXT("Parallel actual tangent and normal are rejected independently of length"),
        ParallelBasis->GetObjectField(TEXT("pairs"))->GetObjectField(TEXT("xz"))->GetNumberField(TEXT("nonOrthogonal")), 3.);
    TestEqual(TEXT("Parallel axes produce invalid bases"), ParallelBasis->GetNumberField(TEXT("invalidVertices")), 3.);
    TestTrue(TEXT("Nonorthogonal sample identifies the exact failed pair"), ParallelBasis->GetArrayField(TEXT("badVertexSamples"))[0]
        ->AsObject()->GetObjectField(TEXT("pairFlags"))->GetObjectField(TEXT("xz"))->GetBoolField(TEXT("nonOrthogonal")));
    for (uint32 Vertex = 0; Vertex < Buffer.GetNumVertices(); ++Vertex)
        Buffer.SetVertexTangents(Vertex, FVector3f(.5f,0,0), FVector3f(0,1,0), FVector3f(0,0,1));
    const auto ShortBasis = Diagnose(); if (!ShortBasis) return false;
    TestEqual(TEXT("Finite short tangents cannot pass unit checks"), ShortBasis->GetObjectField(TEXT("axes"))->GetObjectField(TEXT("x"))->GetNumberField(TEXT("nonUnit")), 3.);
    TestEqual(TEXT("Short reconstructed binormals cannot pass unit checks"), ShortBasis->GetObjectField(TEXT("axes"))->GetObjectField(TEXT("y"))->GetNumberField(TEXT("nonUnit")), 3.);
    const FVector3f RotatedX = FVector3f(1,-1,0).GetSafeNormal(), RotatedZ = FVector3f(1,1,1).GetSafeNormal();
    const FVector3f RotatedY = FVector3f::CrossProduct(RotatedZ, RotatedX);
    for (uint32 Vertex = 0; Vertex < Buffer.GetNumVertices(); ++Vertex)
        Buffer.SetVertexTangents(Vertex, RotatedX, RotatedY, RotatedZ);
    const auto RotatedBasis = Diagnose(); if (!RotatedBasis) return false;
    TestEqual(TEXT("Ordinary packed rounding of a rotated unit basis is accepted"), RotatedBasis->GetNumberField(TEXT("invalidVertices")), 0.);
    TestEqual(TEXT("Packed rotated axes remain orthogonal"), RotatedBasis->GetNumberField(TEXT("orthogonalVertices")), 3.);

    TArray<FVector> SamplePositions, SampleNormals; TArray<FVector2D> SampleUVs; TArray<int32> SampleIndices;
    for (int32 Triangle = 0; Triangle < 22; ++Triangle)
    {
        const int32 First = SamplePositions.Num(); const double Offset = Triangle * 200.;
        SamplePositions.Append({FVector(Offset,0,0), FVector(Offset+100,0,0), FVector(Offset,100,0)});
        SampleNormals.Append({FVector::UpVector, FVector::UpVector, FVector::UpVector});
        SampleUVs.Append({FVector2D(0,0), FVector2D(1,0), FVector2D(0,1)}); SampleIndices.Append({First,First+2,First+1});
    }
    auto* BoundedMesh = UWarImportLibrary::CreateWorldSurface(TEXT("CitadelImportAutomation"),
        FString(TEXT("Samples_")) + FGuid::NewGuid().ToString(EGuidFormats::Digits), SamplePositions, SampleIndices,
        SampleNormals, SampleUVs, UMaterial::GetDefaultMaterial(MD_Surface), false);
    if (!TestNotNull(TEXT("Actual bounded diagnostic fixture was built"), BoundedMesh)) return false;
    UWarImportLibrary::DescribeStaticMeshRenderData(BoundedMesh);
    if (!TestNotNull(TEXT("Bounded fixture has actual compiled render data"), BoundedMesh->GetRenderData())) return false;
    auto& BoundedBuffer = BoundedMesh->GetRenderData()->LODResources[0].VertexBuffers.StaticMeshVertexBuffer;
    for (uint32 Vertex = 0; Vertex < BoundedBuffer.GetNumVertices(); ++Vertex)
        BoundedBuffer.SetVertexTangents(Vertex, FVector3f::ZeroVector, FVector3f(0,1,0), FVector3f(0,0,1));
    TSharedPtr<FJsonObject> BoundedReport;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(BoundedMesh)), BoundedReport)) return false;
    const auto BoundedBasis = BoundedReport->GetArrayField(TEXT("lods"))[0]->AsObject()->GetObjectField(TEXT("tangentBasis"));
    TestEqual(TEXT("Aggregate diagnostics still count every failed actual vertex"), BoundedBasis->GetNumberField(TEXT("invalidVertices")), 66.);
    TestEqual(TEXT("Bad-vertex payload has a fixed native limit"), BoundedBasis->GetNumberField(TEXT("badVertexSampleLimit")), 64.);
    TestEqual(TEXT("Large failures keep only the first64 actual samples"), BoundedBasis->GetArrayField(TEXT("badVertexSamples")).Num(), 64);
    TestTrue(TEXT("Truncated bad-vertex evidence is explicitly disclosed"), BoundedBasis->GetBoolField(TEXT("badVertexSamplesTruncated")));

    auto* HardEdge=UWarImportLibrary::CreateWorldSurface(TEXT("CitadelImportAutomation"),
        FString(TEXT("HardEdge_"))+FGuid::NewGuid().ToString(EGuidFormats::Digits),
        {{0,0,0},{100,0,0},{0,100,0},{0,0,0},{0,100,0},{0,0,100}}, {0,2,1,3,5,4},
        {{0,0,1},{0,0,1},{0,0,1},{1,0,0},{1,0,0},{1,0,0}},
        {{0,0},{1,0},{0,1},{0,0},{0,1},{1,0}}, UMaterial::GetDefaultMaterial(MD_Surface),false);
    if (!TestNotNull(TEXT("Hard-edge native fixture built"),HardEdge)) return false;
    TSharedPtr<FJsonObject> EdgeGood;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(
        UWarImportLibrary::DescribeStaticMeshRenderData(HardEdge)), EdgeGood)) return false;
    TestEqual(TEXT("Both hard-edge faces retain correct corner attributes"), EdgeGood->GetArrayField(TEXT("lods"))[0]
        ->AsObject()->GetNumberField(TEXT("committedSourceTriangleMatches")), 2.);
    auto& Resources=HardEdge->GetRenderData()->LODResources[0];
    auto& EdgeBuffer=Resources.VertexBuffers.StaticMeshVertexBuffer;
    uint32 FloorCorner = MAX_uint32;
    for (uint32 Vertex=0;Vertex<EdgeBuffer.GetNumVertices();++Vertex)
        if (Resources.VertexBuffers.PositionVertexBuffer.VertexPosition(Vertex).IsNearlyZero()
            && FVector3f(EdgeBuffer.VertexTangentZ(Vertex)).Z>.99f)
        {
            FloorCorner = Vertex;
            // Position and UV are shared; the other face's normal is still the wrong normal for this corner.
            EdgeBuffer.SetVertexTangents(Vertex,FVector3f(0,1,0),FVector3f(0,0,1),FVector3f(1,0,0));
            break;
        }
    if (FloorCorner == MAX_uint32) return false;
    TSharedPtr<FJsonObject> Swapped;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(HardEdge)),Swapped)) return false;
    const auto SwappedRow=Swapped->GetArrayField(TEXT("lods"))[0]->AsObject();
    TestEqual(TEXT("Position-only matching cannot detect a different coincident face normal"),
        SwappedRow->GetNumberField(TEXT("committedSourceNormalDifferent")),0.);
    TestEqual(TEXT("Oriented source face matching rejects the hard-edge normal swap"),
        SwappedRow->GetNumberField(TEXT("committedSourceTrianglesDifferent")),1.);
    EdgeBuffer.SetVertexTangents(FloorCorner, FVector3f(1,0,0), FVector3f(0,1,0), FVector3f(0,0,1));
    EdgeBuffer.SetVertexUV(FloorCorner, 0, FVector2f(.25f,.25f));
    TSharedPtr<FJsonObject> WrongUV;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(
        UWarImportLibrary::DescribeStaticMeshRenderData(HardEdge)), WrongUV)) return false;
    const auto WrongUVRow = WrongUV->GetArrayField(TEXT("lods"))[0]->AsObject();
    TestEqual(TEXT("A UV-only corruption retains valid source normals"),
        WrongUVRow->GetNumberField(TEXT("committedSourceNormalDifferent")), 0.);
    TestEqual(TEXT("Oriented source face matching rejects a finite but incorrect UV"),
        WrongUVRow->GetNumberField(TEXT("committedSourceTrianglesDifferent")), 1.);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelSurfaceLodsTest, "AegisWar.Foundation.CitadelSurfaceLods",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCitadelSurfaceLodsTest::RunTest(const FString& Parameters)
{
    TestFalse(TEXT("Missing mesh cannot be configured"), UWarImportLibrary::ConfigureCitadelSurfaceLods(nullptr));
    TArray<FVector> Positions, Normals; TArray<FVector2D> UVs; TArray<int32> Indices;
    for (int32 Triangle = 0; Triangle < 22; ++Triangle)
    {
        const int32 First = Positions.Num(); const double Offset = Triangle * 200.;
        Positions.Append({FVector(Offset,0,0), FVector(Offset+100,0,0), FVector(Offset,100,0)});
        Normals.Append({FVector::UpVector, FVector::UpVector, FVector::UpVector});
        UVs.Append({FVector2D(0,0), FVector2D(1,0), FVector2D(0,1)});
        Indices.Append({First,First+2,First+1});
    }
    const FString Collection = TEXT("AegisCitadel_") + FGuid::NewGuid().ToString(EGuidFormats::Digits).ToLower().Left(12);
    const FString Key = TEXT("SM_Automation_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto* Mesh = UWarImportLibrary::CreateWorldSurface(Collection, Key, Positions, Indices, Normals, UVs,
        UMaterial::GetDefaultMaterial(MD_Surface), true);
    if (!TestNotNull(TEXT("Owned unsaved native fixture was built"), Mesh)) return false;
    UWarImportLibrary::DescribeStaticMeshRenderData(Mesh);
    if (!TestNotNull(TEXT("Owned fixture retains source0"), Mesh->GetMeshDescription(0))) return false;
    if (!TestNotNull(TEXT("Collision fixture has native body setup"), Mesh->GetBodySetup())) return false;

    struct FSourceCorners
    {
        TArray<FVector3f> Positions, Normals;
        TArray<FVector2f> UVs;
        TArray<FIntVector> Triangles;
        TArray<FName> MaterialSlots;
    };
    const auto ReadCorners = [](const UStaticMesh* Surface)
    {
        FSourceCorners Result;
        const FMeshDescription* Description = Surface->GetMeshDescription(0);
        const FStaticMeshConstAttributes Attributes(*Description);
        const auto SourcePositions = Attributes.GetVertexPositions();
        const auto SourceNormals = Attributes.GetVertexInstanceNormals();
        const auto SourceUVs = Attributes.GetVertexInstanceUVs();
        const auto SourceSlots = Attributes.GetPolygonGroupMaterialSlotNames();
        for (const FVertexID Vertex : Description->Vertices().GetElementIDs()) Result.Positions.Add(SourcePositions[Vertex]);
        for (const FVertexInstanceID Corner : Description->VertexInstances().GetElementIDs())
        {
            Result.Normals.Add(SourceNormals[Corner]);
            Result.UVs.Add(SourceUVs.Get(Corner, 0));
        }
        for (const FTriangleID Triangle : Description->Triangles().GetElementIDs())
        {
            const auto Corners = Description->GetTriangleVertexInstances(Triangle);
            Result.Triangles.Add(FIntVector(Corners[0].GetValue(), Corners[1].GetValue(), Corners[2].GetValue()));
            Result.MaterialSlots.Add(SourceSlots[Description->GetTrianglePolygonGroup(Triangle)]);
        }
        return Result;
    };
    const FSourceCorners Original = ReadCorners(Mesh);
    const FMeshBuildSettings OriginalSettings = Mesh->GetSourceModel(0).BuildSettings;
    FMeshBuildSettings Expected = OriginalSettings;
    Expected.bRecomputeNormals = false; Expected.bRecomputeTangents = true; Expected.bUseMikkTSpace = true;
    Expected.bComputeWeightedNormals = false; Expected.bGenerateLightmapUVs = true;
    Expected.SrcLightmapIndex = 0; Expected.DstLightmapIndex = 1; Expected.MinLightmapResolution = 64;
    Expected.bUseFullPrecisionUVs = true; Expected.bUseHighPrecisionTangentBasis = true;
    const FMeshReductionSettings OriginalReduction = Mesh->GetSourceModel(0).ReductionSettings;
    const TArray<FStaticMaterial> OriginalMaterials = Mesh->GetStaticMaterials();
    const ECollisionTraceFlag OriginalCollision = Mesh->GetBodySetup()->CollisionTraceFlag;
    const bool OriginalDoubleSided = Mesh->GetBodySetup()->bDoubleSidedGeometry;
    const FString Owner = Mesh->GetOutermost()->GetMetaData().GetValue(Mesh, TEXT("WarCapitalTerrain"));
    TestFalse(TEXT("Technical fixture has no saved native package"), FPackageName::DoesPackageExist(Mesh->GetOutermost()->GetName()));

    // A matching package path is insufficient: the generated ownership record must match too.
    Mesh->GetOutermost()->GetMetaData().SetValue(Mesh, TEXT("WarCapitalTerrain"), TEXT("ForeignOwner"));
    TestFalse(TEXT("Spoofed generated namespace cannot edit a foreign mesh"), UWarImportLibrary::ConfigureCitadelSurfaceLods(Mesh));
    TestTrue(TEXT("Rejected ownership leaves settings unchanged"), Mesh->GetSourceModel(0).BuildSettings == OriginalSettings);
    TestEqual(TEXT("Rejected ownership leaves source LOD count unchanged"), Mesh->GetNumSourceModels(), 1);
    Mesh->GetOutermost()->GetMetaData().SetValue(Mesh, TEXT("WarCapitalTerrain"), *Owner);
    Mesh->LODForCollision = 1;
    TestFalse(TEXT("Non-LOD0 collision cannot be silently changed"), UWarImportLibrary::ConfigureCitadelSurfaceLods(Mesh));
    TestEqual(TEXT("Rejected collision policy is retained"), Mesh->LODForCollision, 1);
    TestTrue(TEXT("Rejected collision policy leaves source build settings unchanged"), Mesh->GetSourceModel(0).BuildSettings == OriginalSettings);
    Mesh->LODForCollision = 0;

    TArray<int32> FirstTriangles, FirstVertices;
    for (int32 Invocation = 0; Invocation < 2; ++Invocation)
    {
        if (!TestTrue(TEXT("Owned surface policy builds successfully"), UWarImportLibrary::ConfigureCitadelSurfaceLods(Mesh))) return false;
        TestEqual(TEXT("Exactly three native source LODs are configured"), Mesh->GetNumSourceModels(), 3);
        TestTrue(TEXT("Native screen sizes retain automatic computation"), Mesh->GetAutoComputeLODScreenSize());
        TestEqual(TEXT("Signed lightmap channel is retained"), Mesh->GetLightMapCoordinateIndex(), 1);
        TestEqual(TEXT("Signed lightmap resolution is retained"), Mesh->GetLightMapResolution(), 128);
        TestTrue(TEXT("Actual render-buffer inspection remains possible"), bool(Mesh->bAllowCPUAccess));
        TestEqual(TEXT("Route collision uses original LOD0"), Mesh->LODForCollision, 0);
        TestTrue(TEXT("Collision trace policy is unchanged"), Mesh->GetBodySetup()->CollisionTraceFlag == OriginalCollision);
        TestEqual(TEXT("Two-sided collision policy is unchanged"), bool(Mesh->GetBodySetup()->bDoubleSidedGeometry), OriginalDoubleSided);
        TestEqual(TEXT("Source material slots are preserved"), Mesh->GetStaticMaterials().Num(), OriginalMaterials.Num());
        for (int32 Slot = 0; Slot < OriginalMaterials.Num(); ++Slot)
        {
            TestTrue(TEXT("Source material asset is unchanged"), Mesh->GetStaticMaterials()[Slot].MaterialInterface == OriginalMaterials[Slot].MaterialInterface);
            TestEqual(TEXT("Source material slot identity is unchanged"), Mesh->GetStaticMaterials()[Slot].MaterialSlotName, OriginalMaterials[Slot].MaterialSlotName);
        }
        constexpr float Percentages[] = {1.f, .65f, .3f};
        constexpr float ScreenSizes[] = {1.f, .4f, .15f};
        for (int32 Lod = 0; Lod < 3; ++Lod)
        {
            const FStaticMeshSourceModel& Source = Mesh->GetSourceModel(Lod);
            TestTrue(TEXT("Every LOD preserves all signed and inherited build settings"), Source.BuildSettings == Expected);
            FMeshReductionSettings Reduction = OriginalReduction;
            Reduction.PercentTriangles = Percentages[Lod];
            TestTrue(TEXT("Reduction defaults are inherited without policy changes"), Source.ReductionSettings == Reduction);
            TestEqual(TEXT("Requested LOD screen size is retained"), Source.ScreenSize.Default, ScreenSizes[Lod]);
        }
        const FSourceCorners Current = ReadCorners(Mesh);
        TestTrue(TEXT("LOD0 source positions remain exact"), Current.Positions == Original.Positions);
        TestTrue(TEXT("LOD0 supplied outward corner normals remain exact"), Current.Normals == Original.Normals);
        TestTrue(TEXT("LOD0 UV0 corner values remain exact"), Current.UVs == Original.UVs);
        TestTrue(TEXT("LOD0 oriented triangles remain exact"), Current.Triangles == Original.Triangles);
        TestTrue(TEXT("LOD0 triangle material assignments remain exact"), Current.MaterialSlots == Original.MaterialSlots);
        TSharedPtr<FJsonObject> Audit;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshRenderData(Mesh)), Audit)) return false;
        const auto Lods = Audit->GetArrayField(TEXT("lods"));
        if (!TestEqual(TEXT("Three actual render LODs were built"), Lods.Num(), 3)) return false;
        for (int32 Lod = 0; Lod < 3; ++Lod)
        {
            const auto Row = Lods[Lod]->AsObject();
            TestTrue(TEXT("Reduction render LOD is CPU readable"), Row->GetBoolField(TEXT("cpuReadable")));
            TestTrue(TEXT("Each render LOD retains actual UVs"), Row->GetNumberField(TEXT("uvChannels")) >= 1.);
            TestTrue(TEXT("Each render LOD has real vertices and triangles"), Row->GetNumberField(TEXT("vertices")) > 0. && Row->GetNumberField(TEXT("indices")) > 0.);
            const auto Basis = Row->GetObjectField(TEXT("tangentBasis"));
            TestTrue(TEXT("All LODs use actual high-precision tangent buffers"), Basis->GetBoolField(TEXT("highPrecision")));
            TestEqual(TEXT("Temporary healthy mesh has no invalid basis after reduction"), Basis->GetNumberField(TEXT("invalidVertices")), 0.);
            if (Invocation == 0)
            {
                FirstTriangles.Add(int32(Row->GetNumberField(TEXT("indices"))) / 3);
                FirstVertices.Add(int32(Row->GetNumberField(TEXT("vertices"))));
            }
            else
            {
                TestEqual(TEXT("Repeated build retains actual reduced triangle counts"), int32(Row->GetNumberField(TEXT("indices"))) / 3, FirstTriangles[Lod]);
                TestEqual(TEXT("Repeated build retains actual reduced vertex counts"), int32(Row->GetNumberField(TEXT("vertices"))), FirstVertices[Lod]);
            }
        }
        const auto SourceAudit = Lods[0]->AsObject();
        TestEqual(TEXT("Built LOD0 matches all committed oriented faces"), SourceAudit->GetNumberField(TEXT("committedSourceTriangleMatches")), 22.);
        TestEqual(TEXT("No committed face is lost"), SourceAudit->GetNumberField(TEXT("committedSourceTrianglesMissing")), 0.);
        TestEqual(TEXT("No built corner changes source UVs or normals"), SourceAudit->GetNumberField(TEXT("committedSourceTrianglesDifferent")), 0.);
        TestFalse(TEXT("Policy build never saves a Content package"), FPackageName::DoesPackageExist(Mesh->GetOutermost()->GetName()));
    }
    auto* Unowned = UWarImportLibrary::CreateWorldSurface(TEXT("CitadelImportAutomation"),
        TEXT("Unowned_") + FGuid::NewGuid().ToString(EGuidFormats::Digits), Positions, Indices, Normals, UVs,
        UMaterial::GetDefaultMaterial(MD_Surface), false);
    if (!TestNotNull(TEXT("Unowned unsaved fixture is available"), Unowned)) return false;
    const FMeshBuildSettings UnownedSettings = Unowned->GetSourceModel(0).BuildSettings;
    TestFalse(TEXT("Other generated world assets are outside this helper's authority"), UWarImportLibrary::ConfigureCitadelSurfaceLods(Unowned));
    TestEqual(TEXT("Rejected world asset retains its source count"), Unowned->GetNumSourceModels(), 1);
    TestTrue(TEXT("Rejected world asset retains its original policy"), Unowned->GetSourceModel(0).BuildSettings == UnownedSettings);
    auto* Uppercase = UWarImportLibrary::CreateWorldSurface(TEXT("AegisCitadel_ABCDEF123456"),
        TEXT("SM_Uppercase_") + FGuid::NewGuid().ToString(EGuidFormats::Digits), Positions, Indices, Normals, UVs,
        UMaterial::GetDefaultMaterial(MD_Surface), false);
    if (!TestNotNull(TEXT("Uppercase ownership fixture is available"), Uppercase)) return false;
    const FMeshBuildSettings UppercaseSettings = Uppercase->GetSourceModel(0).BuildSettings;
    TestFalse(TEXT("Noncanonical uppercase signature namespace cannot be configured"), UWarImportLibrary::ConfigureCitadelSurfaceLods(Uppercase));
    TestEqual(TEXT("Rejected uppercase namespace retains its source count"), Uppercase->GetNumSourceModels(), 1);
    TestTrue(TEXT("Rejected uppercase namespace retains its policy"), Uppercase->GetSourceModel(0).BuildSettings == UppercaseSettings);
    TestFalse(TEXT("Rejected uppercase namespace is not saved"), FPackageName::DoesPackageExist(Uppercase->GetOutermost()->GetName()));
    return true;
}
#endif
