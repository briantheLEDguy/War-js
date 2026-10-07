#include "WarMageMeshBufferReadback.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"

namespace
{
FString Encode(const TSharedRef<FJsonObject>& Object)
{
    FString Result;
    FJsonSerializer::Serialize(Object,TJsonWriterFactory<>::Create(&Result));
    return Result;
}

FString Unavailable(const TCHAR* Reason)
{
    auto Result=MakeShared<FJsonObject>();
    Result->SetNumberField(TEXT("schemaVersion"),1);
    Result->SetBoolField(TEXT("nativeRenderBuffersRead"),false);
    Result->SetStringField(TEXT("error"),Reason);
    return Encode(Result);
}

template<typename T>
TArray<TSharedPtr<FJsonValue>> Vector3(const T& V)
{
    return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};
}

bool AllowedMesh(const USkeletalMesh* Mesh)
{
    if (!IsValid(Mesh)) return false;
    if (Mesh->GetPathName()==TEXT("/Game/Characters/Models/civic_ember_arcanist_m/ee34f1390d41/civic_ember_arcanist_m.civic_ember_arcanist_m")) return true;
    const FString Prefix(TEXT("/Game/Characters/MageFaceDiagnostic/"));
    const FString Package=Mesh->GetOutermost()->GetName();
    if (!Package.StartsWith(Prefix)) return false;
    FString Candidate,Asset;
    if (!Package.RightChop(Prefix.Len()).Split(TEXT("/"),&Candidate,&Asset) ||
        !Candidate.StartsWith(TEXT("finish_body_b6f6b724c45a")) || Candidate.Len()>96 || Asset.IsEmpty()) return false;
    for (const TCHAR C:Candidate)
        if (!((C>=TEXT('a')&&C<=TEXT('z'))||(C>=TEXT('0')&&C<=TEXT('9'))||C==TEXT('_'))) return false;
    return true;
}
}

FString UWarMageMeshBufferReadback::DescribeFaceRenderBuffers(const USkeletalMesh* Mesh,
    const TArray<int32>& MaterialSlots)
{
    if (!IsInGameThread() || !AllowedMesh(Mesh)) return Unavailable(TEXT("invalid_thread_or_mesh_scope"));
    const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
    if (Ref.GetNum()!=57 || Ref.GetRefBonePose().Num()!=57) return Unavailable(TEXT("unexpected_rig"));
    for (const FTransform& T:Ref.GetRefBonePose()) if (T.ContainsNaN()) return Unavailable(TEXT("nonfinite_reference"));
    const auto& Materials=Mesh->GetMaterials();
    TSet<int32> Selected;
    for (const int32 I:MaterialSlots)
    {
        if (!Materials.IsValidIndex(I)) return Unavailable(TEXT("invalid_material_slot"));
        Selected.Add(I);
    }
    if (Selected.IsEmpty() || Selected.Num()>16) return Unavailable(TEXT("empty_or_excess_material_selection"));
    const FSkeletalMeshRenderData* Data=Mesh->GetResourceForRendering();
    if (!Data || Data->LODRenderData.IsEmpty()) return Unavailable(TEXT("lod0_render_data_unavailable"));
    const FSkeletalMeshLODRenderData& LOD=Data->LODRenderData[0];
    const auto& Position=LOD.StaticVertexBuffers.PositionVertexBuffer;
    const auto& Static=LOD.StaticVertexBuffers.StaticMeshVertexBuffer;
    const auto& Weights=LOD.SkinWeightVertexBuffer;
    const uint32 Count=Position.GetNumVertices();
    if (Count<1 || Count>1000000 || !Position.GetVertexData() || Static.GetNumVertices()!=Count ||
        !Static.GetTangentData() || !Static.GetTexCoordData() || Static.GetNumTexCoords()<1 ||
        Weights.GetNumVertices()!=Count || !Weights.GetDataVertexBuffer()->GetWeightData() ||
        Weights.GetMaxBoneInfluences()>MAX_TOTAL_INFLUENCES ||
        (Weights.GetVariableBonesPerVertex() && (!Weights.GetLookupVertexBuffer()->GetLookupData() ||
            Weights.GetLookupVertexBuffer()->GetNumVertices()!=Count)))
        return Unavailable(TEXT("required_cpu_render_buffers_unavailable"));
    if (!LOD.MultiSizeIndexContainer.IsIndexBufferValid()) return Unavailable(TEXT("index_buffer_unavailable"));
    const auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
    if (!Indices || Indices->Num()<3 || Indices->Num()>3000000 ||
        Indices->GetResourceDataSize()<Indices->Num()*int32(LOD.MultiSizeIndexContainer.GetDataTypeSize()))
        return Unavailable(TEXT("cpu_index_data_unavailable"));

    auto Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> BoneNames,Vertices,Sections;
    for (int32 I=0;I<Ref.GetNum();++I) BoneNames.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));
    uint64 TriangleCount=0;
    TSet<int32> FoundSlots;
    for (int32 SectionIndex=0;SectionIndex<LOD.RenderSections.Num();++SectionIndex)
    {
        const auto& Section=LOD.RenderSections[SectionIndex];
        if (!Selected.Contains(Section.MaterialIndex)) continue;
        if (Section.bDisabled || Section.HasClothingData() || Section.NumTriangles==0 ||
            uint64(Section.BaseVertexIndex)+Section.NumVertices>Count ||
            uint64(Section.BaseIndex)+uint64(Section.NumTriangles)*3>uint64(Indices->Num()))
            return Unavailable(TEXT("invalid_disabled_or_cloth_section"));
        TriangleCount+=Section.NumTriangles;
        if (TriangleCount>500000) return Unavailable(TEXT("excess_triangles"));
        FoundSlots.Add(Section.MaterialIndex);
        TSet<uint32> Referenced;
        TArray<TSharedPtr<FJsonValue>> TriangleIndices;
        for (uint32 I=0;I<Section.NumTriangles*3;++I)
        {
            const uint32 Vertex=Indices->Get(Section.BaseIndex+I);
            if (Vertex<Section.BaseVertexIndex || Vertex>=Section.BaseVertexIndex+Section.NumVertices)
                return Unavailable(TEXT("triangle_escapes_section_vertices"));
            Referenced.Add(Vertex);TriangleIndices.Add(MakeShared<FJsonValueNumber>(Vertex));
        }
        TArray<uint32> Ordered=Referenced.Array();Ordered.Sort();
        for (const uint32 Vertex:Ordered)
        {
            const auto P=Position.VertexPosition(Vertex);const auto N=Static.VertexTangentZ(Vertex);const auto UV=Static.GetVertexUV(Vertex,0);
            if (P.ContainsNaN() || N.ContainsNaN() || UV.ContainsNaN()) return Unavailable(TEXT("nonfinite_vertex"));
            uint32 WeightOffset=0,InfluenceCount=0;
            Weights.GetVertexInfluenceOffsetCount(Vertex,WeightOffset,InfluenceCount);
            if (InfluenceCount==0 || InfluenceCount>MAX_TOTAL_INFLUENCES ||
                uint64(WeightOffset)+uint64(InfluenceCount)*Weights.GetBoneIndexAndWeightByteSize()>
                    Weights.GetDataVertexBuffer()->GetVertexDataSize())
                return Unavailable(TEXT("invalid_vertex_weight_range"));
            const FSkinWeightInfo Skin=Weights.GetVertexSkinWeights(Vertex);
            TArray<TSharedPtr<FJsonValue>> Influences;uint32 Sum=0;
            for (int32 I=0;I<MAX_TOTAL_INFLUENCES;++I)
            {
                const uint16 Weight=Skin.InfluenceWeights[I];if (Weight==0) continue;
                const uint32 LocalBone=Skin.InfluenceBones[I];
                if (!Section.BoneMap.IsValidIndex(LocalBone)) return Unavailable(TEXT("invalid_section_bone"));
                const int32 Bone=Section.BoneMap[LocalBone];
                if (!Ref.IsValidIndex(Bone)) return Unavailable(TEXT("invalid_reference_bone"));
                auto Influence=MakeShared<FJsonObject>();
                Influence->SetNumberField(TEXT("boneIndex"),Bone);Influence->SetStringField(TEXT("boneName"),Ref.GetBoneName(Bone).ToString());
                Influence->SetNumberField(TEXT("weightU16"),Weight);Influences.Add(MakeShared<FJsonValueObject>(Influence));Sum+=Weight;
            }
            if (Influences.IsEmpty() || Sum==0) return Unavailable(TEXT("unweighted_vertex"));
            auto Row=MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("section"),SectionIndex);Row->SetNumberField(TEXT("nativeVertex"),Vertex);
            Row->SetNumberField(TEXT("materialIndex"),Section.MaterialIndex);Row->SetArrayField(TEXT("positionCm"),Vector3(P));
            Row->SetArrayField(TEXT("normal"),Vector3(N));
            Row->SetArrayField(TEXT("uv0"),{MakeShared<FJsonValueNumber>(UV.X),MakeShared<FJsonValueNumber>(UV.Y)});
            Row->SetArrayField(TEXT("influences"),Influences);Row->SetNumberField(TEXT("weightSumU16"),Sum);
            Vertices.Add(MakeShared<FJsonValueObject>(Row));
        }
        auto Row=MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("section"),SectionIndex);Row->SetNumberField(TEXT("materialIndex"),Section.MaterialIndex);
        Row->SetStringField(TEXT("importedMaterialSlot"),Materials[Section.MaterialIndex].ImportedMaterialSlotName.ToString());
        Row->SetNumberField(TEXT("baseVertex"),Section.BaseVertexIndex);Row->SetNumberField(TEXT("numVertices"),Section.NumVertices);
        Row->SetNumberField(TEXT("numTriangles"),Section.NumTriangles);Row->SetArrayField(TEXT("triangleIndices"),TriangleIndices);
        Sections.Add(MakeShared<FJsonValueObject>(Row));
    }
    if (FoundSlots.Num()!=Selected.Num() || Vertices.IsEmpty()) return Unavailable(TEXT("selected_material_missing_rendered_triangles"));
    Result->SetNumberField(TEXT("schemaVersion"),1);Result->SetStringField(TEXT("mesh"),Mesh->GetPathName());
    Result->SetNumberField(TEXT("lod"),0);Result->SetNumberField(TEXT("lodVertexCount"),Count);
    Result->SetBoolField(TEXT("nativeRenderBuffersRead"),true);Result->SetBoolField(TEXT("referencePositionsInCentimeters"),true);
    Result->SetBoolField(TEXT("storedWeightsUse16Bit"),Weights.Use16BitBoneWeight());
    Result->SetNumberField(TEXT("weightGetterNormalizationMaximum"),65535);
    Result->SetArrayField(TEXT("boneNames"),BoneNames);Result->SetArrayField(TEXT("vertices"),Vertices);Result->SetArrayField(TEXT("sections"),Sections);
    Result->SetBoolField(TEXT("geometryComparedToSource"),false);Result->SetBoolField(TEXT("visualApproved"),false);
    return Encode(Result);
}
