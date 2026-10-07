// Unsaved synthetic native CPU render buffers; no RHI initialization, visible model, saves or artwork approval.
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarMageMeshBufferReadback.h"
#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Async/Async.h"

namespace WarMageBufferTests
{
constexpr EAutomationTestFlags Flags=EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter;

USkeletalMesh* Fixture(bool WithBuffers)
{
    const FString Root=TEXT("/Game/Characters/MageFaceDiagnostic/finish_body_b6f6b724c45a_buffer_")+
        FGuid::NewGuid().ToString(EGuidFormats::Digits).ToLower();
    UPackage* Package=CreatePackage(*(Root+TEXT("/Fixture")));Package->SetFlags(RF_Transient);
    USkeletalMesh* Mesh=NewObject<USkeletalMesh>(Package,TEXT("Fixture"),RF_Transient|RF_Transactional);
    FReferenceSkeleton Reference;
    {
        FReferenceSkeletonModifier Modifier(Reference,nullptr);
        for (int32 I=0;I<57;++I)
        {
            const FName Name=I==45 ? FName(TEXT("head")) : FName(*FString::Printf(TEXT("bone_%d"),I));
            Modifier.Add(FMeshBoneInfo(Name,Name.ToString(),I==0 ? INDEX_NONE : 0),FTransform::Identity);
        }
    }
    Mesh->SetRefSkeleton(Reference);
    FSkeletalMaterial Material;Material.ImportedMaterialSlotName=TEXT("ember_finish_face");
    Mesh->SetMaterials({Material});
    if (WithBuffers)
    {
        Mesh->AllocateResourceForRendering();
        auto* Data=Mesh->GetResourceForRendering();Data->LODRenderData.Add(new FSkeletalMeshLODRenderData());
        auto& LOD=Data->LODRenderData[0];
        LOD.StaticVertexBuffers.PositionVertexBuffer.Init(TArray<FVector3f>{FVector3f(0,0,165),FVector3f(1,0,165),FVector3f(0,1,165)},true);
        auto& Static=LOD.StaticVertexBuffers.StaticMeshVertexBuffer;Static.Init(3,1,true);
        for (uint32 I=0;I<3;++I)
        {
            Static.SetVertexTangents(I,FVector3f(1,0,0),FVector3f(0,1,0),FVector3f(0,0,1));
            Static.SetVertexUV(I,0,FVector2f(.25f,.75f));
        }
        FSkinWeightInfo Weight;FMemory::Memzero(Weight);Weight.InfluenceBones[0]=1;Weight.InfluenceWeights[0]=65535;
        LOD.SkinWeightVertexBuffer.SetMaxBoneInfluences(4);
        LOD.SkinWeightVertexBuffer.SetUse16BitBoneIndex(true);LOD.SkinWeightVertexBuffer.SetUse16BitBoneWeight(true);
        LOD.SkinWeightVertexBuffer=TArray<FSkinWeightInfo>{Weight,Weight,Weight};
        LOD.MultiSizeIndexContainer.RebuildIndexBuffer(sizeof(uint16),TArray<uint32>{0,1,2});
        FSkelMeshRenderSection Section;Section.MaterialIndex=0;Section.NumVertices=3;Section.NumTriangles=1;Section.BoneMap={1,45};
        LOD.RenderSections.Add(Section);
    }
    return Mesh;
}

TSharedPtr<FJsonObject> Read(const FString& Text)
{
    TSharedPtr<FJsonObject> Result;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Result);return Result;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageBufferGuardsTest,
    "AegisWar.Foundation.MageBufferReadback.Guards",WarMageBufferTests::Flags)
bool FWarMageBufferGuardsTest::RunTest(const FString& Parameters)
{
    using namespace WarMageBufferTests;
    TestFalse(TEXT("Null is explicit unavailable"),Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(nullptr,{0}))->GetBoolField(TEXT("nativeRenderBuffersRead")));
    USkeletalMesh* Empty=Fixture(false);
    TestFalse(TEXT("Missing CPU buffers are explicit unavailable"),Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Empty,{0}))->GetBoolField(TEXT("nativeRenderBuffersRead")));
    USkeletalMesh* Full=Fixture(true);
    TestFalse(TEXT("Invalid material rejected"),Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Full,{2}))->GetBoolField(TEXT("nativeRenderBuffersRead")));
    TestFalse(TEXT("Empty selection rejected"),Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Full,{}))->GetBoolField(TEXT("nativeRenderBuffersRead")));
    auto Future=Async(EAsyncExecution::Thread,[Full] {return UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Full,{0});});
    TestFalse(TEXT("Off-thread rejects before buffer reads"),Read(Future.Get())->GetBoolField(TEXT("nativeRenderBuffersRead")));
    Full->GetResourceForRendering()->LODRenderData[0].RenderSections[0].BoneMap.Empty();
    TestFalse(TEXT("Invalid section bone map rejected"),Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Full,{0}))->GetBoolField(TEXT("nativeRenderBuffersRead")));
    TestFalse(TEXT("Readback never dirties synthetic package"),Full->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageBufferDecodeTest,
    "AegisWar.Foundation.MageBufferReadback.DecodeAndIsolation",WarMageBufferTests::Flags)
bool FWarMageBufferDecodeTest::RunTest(const FString& Parameters)
{
    using namespace WarMageBufferTests;
    USkeletalMesh* Mesh=Fixture(true);const auto* Data=Mesh->GetResourceForRendering();
    const FString First=UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Mesh,{0});auto Json=Read(First);
    if (!TestTrue(TEXT("Finite native CPU buffers read"),Json.IsValid()&&Json->GetBoolField(TEXT("nativeRenderBuffersRead")))) return false;
    const auto& Vertices=Json->GetArrayField(TEXT("vertices"));TestEqual(TEXT("All triangle vertices included"),Vertices.Num(),3);
    for (const auto& Value:Vertices)
    {
        const auto& Row=Value->AsObject();const auto& Influences=Row->GetArrayField(TEXT("influences"));
        TestEqual(TEXT("Rigid face has one actual influence"),Influences.Num(),1);
        TestEqual(TEXT("Section local bone1 maps to reference head45"),Influences[0]->AsObject()->GetStringField(TEXT("boneName")),FString(TEXT("head")));
        TestEqual(TEXT("Actual weight getter retains full precision"),Influences[0]->AsObject()->GetNumberField(TEXT("weightU16")),65535.);
    }
    TestEqual(TEXT("Repeated native buffer read is exact"),UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(Mesh,{0}),First);
    TestTrue(TEXT("Render resource pointer unchanged"),Mesh->GetResourceForRendering()==Data);
    TestEqual(TEXT("Native source weight unchanged"),Data->LODRenderData[0].SkinWeightVertexBuffer.GetBoneWeight(0,0),uint16(65535));
    TestEqual(TEXT("Native source index unchanged"),Data->LODRenderData[0].MultiSizeIndexContainer.GetIndexBuffer()->Get(1),uint32(1));
    TestFalse(TEXT("Native readback leaves fixture clean"),Mesh->GetOutermost()->IsDirty());
    USkeletalMesh* EightBit=Fixture(true);
    auto& EightBitWeights=EightBit->GetResourceForRendering()->LODRenderData[0].SkinWeightVertexBuffer;
    FSkinWeightInfo Rigid;FMemory::Memzero(Rigid);Rigid.InfluenceBones[0]=1;Rigid.InfluenceWeights[0]=65535;
    EightBitWeights.SetUse16BitBoneWeight(false);EightBitWeights=TArray<FSkinWeightInfo>{Rigid,Rigid,Rigid};
    auto ByteJson=Read(UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(EightBit,{0}));
    if (!TestTrue(TEXT("Eight-bit CPU weight buffer read"),ByteJson.IsValid()&&ByteJson->GetBoolField(TEXT("nativeRenderBuffersRead")))) return false;
    TestFalse(TEXT("Fixture actually stores eight-bit weights"),ByteJson->GetBoolField(TEXT("storedWeightsUse16Bit")));
    const auto& ByteInfluence=ByteJson->GetArrayField(TEXT("vertices"))[0]->AsObject()->GetArrayField(TEXT("influences"))[0]->AsObject();
    TestEqual(TEXT("Eight-bit getter expands byte255 to uint16 65535"),ByteInfluence->GetNumberField(TEXT("weightU16")),65535.);
    TestFalse(TEXT("Eight-bit readback leaves synthetic package clean"),EightBit->GetOutermost()->IsDirty());
    return true;
}
#endif
